# napi.py-3
Napi.py is a simple script that allows you to download subtitles for movies from NapiProjekt and OpenSubtitles.
Check more with build-in help:
````
$ napi.py -h
usage: napi.py [-h] [-l LANGUAGE] [--selection] [-p PREFERRED] filename

positional arguments:
  filename              Path to a movie file

optional arguments:
  -h, --help            show this help message and exit
  -l LANGUAGE, --language LANGUAGE
                        language or list of languages, for example "pol" or
                        "pol,eng". Check in napiprojekt's db only for Polish
                        version. Default value: pol. Available languages: all,
                        tha, afr, alb, ara, arm, ast, aze, baq, bel, ben, bos,
                        bre, bul, bur, cat, chi, zht, zhe, hrv, cze, dan, dut,
                        eng, epo, est, ext, fin, fre, glg, geo, ger, ell, heb,
                        hin, hun, ice, ind, ita, jpn, kan, kaz, khm, kor, kur,
                        lav, lit, ltz, mac, may, mal, mni, mon, mne, nor, oci,
                        per, pol, por, pob, pom, rum, rus, scc, sin, slo, slv,
                        spa, swa, swe, syr, tgl, tam, tel, tur, ukr, urd, vie
  --selection           shows list of available subtitles and allows to select
                        version to download
  -p PREFERRED, --preferred PREFERRED
                        preferred service (available options: napi,
                        opensubtitles). Works only in selection mode. Default:
                        opensubtitles.
napi.py uses NapiProjekt Database (http://www.napiprojekt.pl/) and OpenSubtitles Database (https://www.opensubtitles.org/).

````

# Requirements
GNU/Linux box, Python3. 7z binary is required. 
