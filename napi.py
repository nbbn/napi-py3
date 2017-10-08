#!/usr/bin/env python3
# Jakub Stepniak github.com/nbbn

import urllib.request
import urllib.error
import hashlib
import os
import argparse
import struct
import xmlrpc.client
import time
import zipfile
import sys
import atexit


class SubtitleService:
    def download_subtitle(self, movie_id: str) -> bytes:
        raise NotImplementedError

    def list_available_subtitles(self) -> list:
        raise NotImplementedError

    @staticmethod
    def reformat_subtitle(sub: bytes) -> str:
        try:
            sub = sub.decode('cp1250')
        except UnicodeDecodeError:
            sub = sub.decode('utf-8', 'replace')
        return sub

    @staticmethod
    def save_subtitle_file(sub: str, path: str) -> None:
        with open(path, 'w') as f:
            f.write(sub)

    def __init__(self, file_path: str, lang: str = 'pol') -> None:
        """Using full path to movie file initiate local variables, connection to a service, hash."""

        self.language = lang
        self.file_path = file_path
        self.filename = self.file_path.split('/')[-1].split('\\')[-1]
        self.filename_wo_ext = '.'.join(self.file_path.split('/')[-1].split('\\')[-1].split('.')[:-1])
        self.path = self.file_path[:-len(self.filename)]

        self.subtitle_filename = '{}.txt'.format(self.filename_wo_ext)
        self.subtitle_path = self.path + self.subtitle_filename
        self.download_temp_path_m = '/tmp/napisy_mid'
        self.subtitle_temp_path = '/tmp/{}'.format(self.subtitle_filename)

    def __hash_function(self) -> str:
        raise NotImplementedError


class Napi(SubtitleService):
    def __init__(self, file_path: str, lang: str = 'pol') -> None:
        super().__init__(file_path, lang)
        self.hash_digest = None
        self.file_hash = self.__hash_function()

    def __hash_function(self):
        d = hashlib.md5()
        with open(self.file_path, mode='br') as f:
            d.update(f.read(10485760))
        self.movie_id = d.hexdigest()
        idx = [0xe, 0x3, 0x6, 0x8, 0x2]
        mul = [2, 2, 5, 4, 3]
        add = [0, 0xd, 0x10, 0xb, 0x5]

        b = []
        for i in range(len(idx)):
            a = add[i]
            m = mul[i]
            i = idx[i]

            t = a + int(self.movie_id[i], 16)
            v = int(self.movie_id[t:t + 2], 16)
            b.append(("%x" % (v * m))[-1])
        return ''.join(b)

    def list_available_subtitles(self):
        try:
            self.download_subtitle(self.movie_id)
        except Exception:
            return []
        return [1]

    def download_subtitle(self, movie_id: str = None) -> bytes:
        if movie_id is None:
            movie_id = self.movie_id
        url = "http://napiprojekt.pl/unit_napisy/dl.php?l=PL&f={}&t={}&v=other&kolejka=false&nick=&pass=&napios={}" \
            .format(movie_id, self.file_hash, os.name)
        u = urllib.request.urlopen(url)
        c = u.read()
        code = u.getcode()
        if code == 200 and c != b'NPc0':
            open(self.download_temp_path_m, "bw").write(c)
        else:
            raise ValueError('No napiprojekt subtitle found.')

        if os.system('/usr/bin/7z x -y -so -piBlm8NTigvru0Jr0 {} 2>/dev/null >"{}"'.format(
          self.download_temp_path_m, self.subtitle_temp_path)) == 0:
            os.remove(self.download_temp_path_m)
        else:
            raise EnvironmentError
        with open(self.subtitle_temp_path, 'rb') as f:
            c = f.read()
        os.remove(self.subtitle_temp_path)
        return c

    def download_and_save(self, movie_id: str = None) -> None:
        c = self.download_subtitle(movie_id)
        self.save_subtitle_file(self.reformat_subtitle(c), self.subtitle_path)


class Opensubtitle(SubtitleService):
    def __init__(self, file_path: str, lang: str = 'pol') -> None:
        super().__init__(file_path, lang)
        self.connection_handler = None
        self.token = None
        self.connect()
        self.file_hash = self.__hash_function()

    def __hash_function(self):
        l_format = '<q'  # little-endian long long
        b_size = struct.calcsize(l_format)

        with open(self.file_path, mode='br') as f:
            f_size = os.path.getsize(self.file_path)
            h = f_size

            if f_size < 65536 * 2:
                raise IOError('File to small.')

            for x in range(65536 // b_size):
                buffer = f.read(b_size)
                (l_value,) = struct.unpack(l_format, buffer)
                h += l_value
                h = h & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

            f.seek(max(0, f_size - 65536), 0)
            for x in range(65536 // b_size):
                buffer = f.read(b_size)
                (l_value,) = struct.unpack(l_format, buffer)
                h += l_value
                h = h & 0xFFFFFFFFFFFFFFFF

            return "%016x" % h

    def connect(self):
        p = xmlrpc.client.ServerProxy('https://api.opensubtitles.org:443/xml-rpc')
        a = p.LogIn('', '', '', 'SMPlayer v17.3.0')
        if a['status'] == '200 OK':
            self.token = a['token']
            self.connection_handler = p
        else:
            raise EnvironmentError

    def identify_movie(self) -> str:
        a = self.connection_handler.CheckMovieHash2(self.token, [self.file_hash])
        if a['status'] == '200 OK':
            try:
                a = a['data'][self.file_hash][0]
            except TypeError:
                raise Exception('No information about movie in database.')
            if a['MovieKind'] == 'episode':
                return '{} ({}) S{}E{}'.format(a['MovieName'], a['MovieYear'], a['SeriesSeason'], a['SeriesEpisode'])
            else:
                return '{} ({})'.format(a['MovieName'], a['MovieYear'])

    def list_available_subtitles(self):
        a = self.connection_handler.SearchSubtitles(self.token,
                                                    [{'sublanguageid': self.language, 'moviehash': self.file_hash}])
        if a['status'] == '200 OK':
            return a['data']
        else:
            raise EnvironmentError

    def download_subtitle(self, movie_id: str = None) -> bytes:
        if movie_id is None:
            l = self.list_available_subtitles()
            m = time.strptime('1900-01-01 01:01:01', '%Y-%m-%d %H:%M:%S')
            sub_item = None
            for i in l:
                t = time.strptime(i['SubAddDate'], '%Y-%m-%d %H:%M:%S')
                if t > m:
                    m = t
                    sub_item = i
            url = sub_item['ZipDownloadLink']
            movie_id = url
        # print(movie_id)
        u = urllib.request.urlopen(movie_id)
        c = u.read()
        code = u.getcode()
        if code == 200:
            open(self.download_temp_path_m, "bw").write(c)
            with zipfile.ZipFile(self.download_temp_path_m) as myzip:
                m_size = 0
                n = None
                for i in myzip.filelist:
                    if i.file_size > m_size:
                        n = i.filename
                        m_size = i.file_size
                in_zip_filename = n
                # print(in_zip_filename)
                with myzip.open(in_zip_filename) as f:
                    c = f.read()
        else:
            raise EnvironmentError
        os.remove(self.download_temp_path_m)
        return c

    def download_and_save(self, movie_id: str = None) -> None:
        c = self.download_subtitle(movie_id)
        self.save_subtitle_file(self.reformat_subtitle(c), self.subtitle_path)

    def disconnect(self):
        self.connection_handler.LogOut(self.token)


class Subber:
    languages = ['all', 'tha', 'afr', 'alb', 'ara', 'arm', 'ast', 'aze', 'baq', 'bel', 'ben', 'bos', 'bre', 'bul',
                 'bur', 'cat', 'chi', 'zht', 'zhe', 'hrv', 'cze', 'dan', 'dut', 'eng', 'epo', 'est', 'ext', 'fin',
                 'fre', 'glg', 'geo', 'ger', 'ell', 'heb', 'hin', 'hun', 'ice', 'ind', 'ita', 'jpn', 'kan', 'kaz',
                 'khm', 'kor', 'kur', 'lav', 'lit', 'ltz', 'mac', 'may', 'mal', 'mni', 'mon', 'mne', 'nor', 'oci',
                 'per', 'pol', 'por', 'pob', 'pom', 'rum', 'rus', 'scc', 'sin', 'slo', 'slv', 'spa', 'swa', 'swe',
                 'syr', 'tgl', 'tam', 'tel', 'tur', 'ukr', 'urd', 'vie']

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('filename', help="Path to a movie file", type=self.__parse_filename)
        parser.add_argument('-l', '--language',
                            help='language or list of languages, for example "pol" or "pol,eng". '
                                 'Check in napiprojekt\'s db only for Polish version.'
                                 ' Default value: pol. Available languages: {}'
                            .format(', '.join(self.languages)), default='pol', type=self.__parse_language)
        parser.add_argument('--selection', action='store_true',
                            help='shows list of available subtitles and allows to select version to download')
        parser.add_argument('-p', '--preferred',
                            help='preferred service (available options: napi, opensubtitles). Works only in selection mode. Default: opensubtitles.',
                            type=self.__parse_preferred, default='opensubtitles')

        self.__args = parser.parse_args()
        # print(self.__args)

        self.selection = self.__args.selection
        self.language = self.__args.language
        self.filename = self.__args.filename
        self.preferred = self.__args.preferred
        try:
            with open(self.filename) as f:
                if f.readable() is False:
                    raise EnvironmentError("File not readable.")
        except IOError:
            raise IOError("Movie file not found.")

    def __parse_language(self, lang):
        for i in lang.split(','):
            if i not in self.languages:
                raise argparse.ArgumentError(None, 'Unknown language.')
        return lang

    @staticmethod
    def __parse_preferred(pref):
        if pref in ['napi', 'opensubtitles']:
            return pref
        else:
            raise argparse.ArgumentError(None, 'Unknown preferred service.')

    @staticmethod
    def __parse_filename(fn):
        if not os.path.isfile(fn):
            raise argparse.ArgumentError(None, "Movie file doesn't exists.")
        return fn

    def handler(self):
        napi = Napi(self.filename)
        try:
            open_subtitles = Opensubtitle(self.filename, lang=self.language)
        except IOError as e:
            print(str(e))
            sys.exit()
        try:
            r = open_subtitles.identify_movie()
        except Exception as e:
            print(str(e))
        else:
            print("\nIdentified as: {}".format(r))
        os_l = open_subtitles.list_available_subtitles()
        n_l = napi.list_available_subtitles()
        if len(os_l) == 0 and len(n_l) == 0:
            print('No subtitles found for this movie.')
            sys.exit()
        if self.selection is False:
            print('\n\nNapi subtitles found: {}'.format(len(n_l)))
            print('OpenSubtitle subtitles found: {}'.format(len(os_l)))
            print("\nPreferred service: {}.".format(self.preferred))
            in_action = self.preferred
            try:
                if n_l == 0 and os_l == 0:
                    print('No subtitles found.')
                    sys.exit()
                elif len(n_l) == 0 and self.preferred == 'napi':
                    print("Fallback to opensubtitles.")
                    in_action = 'opensubtitles'
                    napi.download_and_save()
                elif len(os_l) == 0 and self.preferred == 'opensubtitles':
                    print("Fallback to napi.")
                    in_action = 'napi'
                    open_subtitles.download_and_save()
                elif self.preferred == 'download_and_save':
                    napi.download_and_save()
                elif self.preferred == 'opensubtitles':
                    open_subtitles.download_and_save()
                else:
                    raise UnboundLocalError
            except Exception as e:
                print('Subtitle download from {} failed.'.format(in_action))
                print(str(e))
                if in_action == 'napi':
                    in_action = 'opensubtitles'
                    print('Retry with {}'.format(in_action))
                    open_subtitles.download_and_save()
                elif in_action == 'opensubtitles':
                    in_action = 'napi'
                    print('Retry with {}'.format(in_action))
                    napi.download_and_save()
            else:
                print('Subtitle downloaded from {}.'.format(in_action))
        else:
            # self.selection is True
            print(os_l)
            selection = []
            print('\n\nNapi subtitles found: {}'.format(len(n_l)))
            if len(n_l) > 0:
                print('[1] Napi subtitles: {} lines in file'.format(
                    len(napi.reformat_subtitle(napi.download_subtitle()).split('\n'))))
                selection.append('napi')
            print('OpenSubtitle subtitles found: {}'.format(len(os_l)))
            start = len(selection) + 1
            for i, x in enumerate(os_l):
                print('[{}] Opensubtitles, downloads: {}, realease: {}, duration: {}, lang: {}, added: {}, size: {}'
                      .format(i + start, x['SubDownloadsCnt'], x['MovieReleaseName'], x['SubLastTS'],
                              x['SubLanguageID'], x['SubAddDate'], x['SubSize']))
                selection.append(x['ZipDownloadLink'])
            print('\n')
            t = True
            while t:
                try:
                    selected = int(input('\nSelect subtitle to download (number):'))
                    movie_id = selection[selected - 1]
                    if movie_id == 'napi':
                        napi.download_and_save()
                        print('Subtitles successfully downloaded.')
                        t = False
                    else:
                        open_subtitles.download_and_save(movie_id)
                        t = False
                except ValueError:
                    print('invalid subtitle number.')
                except IndexError:
                    print('No subtitle with selected number.')
                except Exception as e:
                    print(str(e))
                else:
                    t = False

    @staticmethod
    def exit_info():
        print(
            '\nnapi.py (https://github.com/nbbn/napi-py3) uses NapiProjekt Database (http://www.napiprojekt.pl/) and OpenSubtitles Database (https://www.opensubtitles.org/).')


if __name__ == '__main__':
    atexit.register(Subber.exit_info)
    s = Subber()
    s.handler()
