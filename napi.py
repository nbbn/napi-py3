#!/usr/bin/env python3
# original file by gim,krzynio,dosiu,hash 2oo8.
# modified by Jakub Stepniak github.com/nbbn

import urllib.request
import urllib.error
import hashlib
import os
import argparse
import struct
import xmlrpc.client
import time
import zipfile

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
                            help='preferred service (available options: napi, opensubtitles). Default: napi',
                            type=self.__parse_preferred, default='napi')
        # todo: prepare logger
        args = parser.parse_args()

        self.selection = args.selection
        self.language = args.language
        self.filename = args.filename
        self.preferred = args.preferred

        self.filename_wo_path = self.filename.split('/')[-1].split('\\')[-1]
        self.filename_wo_path_and_ext = '.'.join(self.filename.split('/')[-1].split('\\')[-1].split('.')[:-1])
        self.filename_path = self.filename[:-len(self.filename_wo_path)]

        self.subtitle_filename = '{}.txt'.format(self.filename_wo_path_and_ext)
        self.subtitle_path = self.filename_path + self.subtitle_filename
        self.temp_file = '/tmp/napisy.7z'
        self.subtitle_temp_path = '/tmp/{}'.format(self.subtitle_filename)
        try:
            self.__init_opensubtitles()
        except EnvironmentError as e:
            self.os_proxy = False
            print(str(e))

    def __init_opensubtitles(self):
        self.os_h = self.__opensubtitles_hash()
        if not isinstance(self.os_h, str):
            return str(self.os_h)
        self.os_proxy = xmlrpc.client.ServerProxy('https://api.opensubtitles.org:443/xml-rpc')
        a = self.os_proxy.LogIn('', '', '', 'SMPlayer v17.3.0')
        if a['status'] == '200 OK':
            self.opensubtitle_token = a['token']
        else:
            raise EnvironmentError('Opensubtitles server not available.')

    def __parse_language(self, lang):
        for i in lang.split(','):
            if i not in self.languages:
                raise argparse.ArgumentError(None, 'Unknown language.')
        return lang

    def __parse_preferred(self, pref):
        if pref in ['napi', 'opensubtitles']:
            return pref
        else:
            raise argparse.ArgumentError(None, 'Unknown preferred service.')

    @staticmethod
    def __parse_filename(fn):
        if not os.path.isfile(fn):
            raise argparse.ArgumentError(None, "Movie file doesn't exists.")
        return fn

    def _check_napi(self):
        """Download and validate subtitle from napi projekt. Subtitle is located in temporary location."""
        d = hashlib.md5()
        with open(self.filename, mode='br') as f:
            d.update(f.read(10485760))
        url = "http://napiprojekt.pl/unit_napisy/dl.php?l=PL&f={}&t={}&v=other&kolejka=false&nick=&pass=&napios={}" \
            .format(d.hexdigest(), self.__napi_hash(d.hexdigest()), os.name)
        try:
            u = urllib.request.urlopen(url)
            c = u.read()
            code = u.getcode()
            if code == 200 and c != b'NPc0':
                open(self.temp_file, "bw").write(c)
            else:
                raise ValueError('No napiprojekt subtitle found.')
        except urllib.error.URLError:
            return "No Internet connection."
        except ValueError as e:
            return str(e)

        try:
            if os.system('/usr/bin/7z x -y -so -piBlm8NTigvru0Jr0 {} 2>/dev/null >"{}"'.format(
                    self.temp_file, self.subtitle_temp_path)) == 0:
                # print('subtitles sucessfully extracted.')
                os.remove(self.temp_file)
            else:
                raise EnvironmentError
        except EnvironmentError as e:
            template = 'An exception of type {0} occurred. Arguments:\n{1!r}'
            return template.format(type(e).__name__, e.args)

        try:
            lines = [line for line in open(self.subtitle_temp_path, 'r', encoding='cp1250')]
            os.remove(self.subtitle_temp_path)
            open(self.subtitle_temp_path, 'w').writelines(lines)
        except Exception as e:
            template = 'Some errors in encoding, keeping buggy version. ' \
                       'An exception of type {0} occurred. Arguments:\n{1!r}'
            message = template.format(type(e).__name__, e.args)
            return message
        return 0

    def _check_name_opensubtitles(self):
        a = self.os_proxy.CheckMovieHash2(self.opensubtitle_token, [self.os_h])
        if a['status'] == '200 OK':
            a = a['data'][self.os_h][0]
            if a['MovieKind'] == 'episode':
                self.recognized_movie = '{} ({}) S{}E{}'.format(a['MovieName'], a['MovieYear'], a['SeriesSeason'],
                                                                a['SeriesEpisode'])
            else:
                self.recognized_movie = '{} ({})'.format(a['MovieName'], a['MovieYear'])

    def _list_opensubtitles(self):
        a = self.os_proxy.SearchSubtitles(self.opensubtitle_token,
                                          [{'sublanguageid': self.language, 'moviehash': self.os_h}])
        if a['status'] == '200 OK':
            return a['data']
        else:
            return None

    def _download_best_opensubtitles(self):
        l = self._list_opensubtitles()
        m = time.strptime('1900-01-01 01:01:01', '%Y-%m-%d %H:%M:%S')
        s = None
        for i in l:
            t = time.strptime(i['SubAddDate'], '%Y-%m-%d %H:%M:%S')
            if t>m:
                m = t
                s = i
        url = s['ZipDownloadLink']
        print(url)
        try:
            u = urllib.request.urlopen(url)
            c = u.read()
            code = u.getcode()
            if code == 200:
                open(self.temp_file+'os', "bw").write(c)
                with zipfile.ZipFile(self.temp_file+'os') as myzip:
                    with myzip.open(s['SubFileName']) as myfile:
                        c = myfile.read().decode('cp1250')
                        with open(self.subtitle_temp_path+'os', 'w') as f:
                            f.write(c)
            else:
                raise ValueError('Opensubtitle server error.')
        except urllib.error.URLError:
            return "No Internet connection."
        except ValueError as e:
            return str(e)

    @staticmethod
    def __napi_hash(z):
        idx = [0xe, 0x3, 0x6, 0x8, 0x2]
        mul = [2, 2, 5, 4, 3]
        add = [0, 0xd, 0x10, 0xb, 0x5]

        b = []
        for i in range(len(idx)):
            a = add[i]
            m = mul[i]
            i = idx[i]

            t = a + int(z[i], 16)
            v = int(z[t:t + 2], 16)
            b.append(("%x" % (v * m))[-1])
        return ''.join(b)

    def __opensubtitles_hash(self):
        try:
            longlongformat = '<q'  # little-endian long long
            bytesize = struct.calcsize(longlongformat)

            with open(self.filename, mode='br') as f:
                filesize = os.path.getsize(self.filename)
                h = filesize

                if filesize < 65536 * 2:
                    return "SizeError"

                for x in range(65536 // bytesize):
                    buffer = f.read(bytesize)
                    (l_value,) = struct.unpack(longlongformat, buffer)
                    h += l_value
                    h = h & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

                f.seek(max(0, filesize - 65536), 0)
                for x in range(65536 // bytesize):
                    buffer = f.read(bytesize)
                    (l_value,) = struct.unpack(longlongformat, buffer)
                    h += l_value
                    h = h & 0xFFFFFFFFFFFFFFFF

                f.close()
                return "%016x" % h

        except IOError:
            return "IOError"

    def handler(self):
        self._check_name_opensubtitles()
        n = self._check_napi()

        print("\nIdentified as: {}".format(self.recognized_movie))
        if n == 0:
            print('\nNapi subtitles:\t\t\tfound.')
        else:
            print('\n{}'.format(n))
        l = self._list_opensubtitles()
        if len(l):
            print('Opensubtitles subtitles:\tfound.')
        else:
            print('Opensubtitles subtitles:\tnot found.')

        print('Preferred: \t\t\t{}'.format(self.preferred))
        self._download_best_opensubtitles()
        print('\n\n\n')
        print()




        pass


if __name__ == '__main__':
    s = Subber()
    s.handler()

    if s.os_proxy:
        s.os_proxy.LogOut(s.opensubtitle_token)
        # print(s.filename, s.language, s.verbose, s.subtitle_filename, s.preferred)

        # s._list_opensubtitles()

        # n = s._check_napi()
        # if n == 0:
        #     print('napi subs successfully downloaded')
        # else:
        #     print('napi failed\n{}'.format(n))
