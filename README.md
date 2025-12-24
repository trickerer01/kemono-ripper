# Kemono ripper

**Kemono ripper** is an advanced kemono.cr / .su / .party scanner / downloader

- Automatically parses posts for external links and downloads everything. Supported sites:
  - [mega.nz](https://mega.nz) (using [mega-download](https://github.com/trickerer01/mega-download/))
  - [mediafire.com](https://mediafire.com) (using [mediafire-download](https://github.com/trickerer01/mediafire-download/))
  - [dropbox.com](https://www.dropbox.com)
  - [webmshare.com](https://webmshare.com)
  - [catbox.moe](https://catbox.moe)
  - Site support requests go to [issues](https://github.com/trickerer01/kemono-ripper/issues)

### Requirements
- **Python 3.10 or greater**
- See `requirements.txt` for additional dependencies. Install with:
  - `python -m pip install -r requirements.txt`
### Usage
##### Install as a module
- `cd kemono-ripper`
- `python -m pip install .`
- `python -m kemono_ripper [options...]` OR simply
- `kemono-ripper [options...]`
##### Without installing
- `cd kemono-ripper`
- Run either:
  - `python kemono_ripper/__main__.py [options...]` OR
  - `kemono-ripper.cmd [options...]` (Windows)
  - `kemono-ripper.sh [options...]` (Linux)

- Invoke `<base...> --help` to list all options

##### Getting started
- In these examples base cmdline is `kemono-ripper.cmd [options...]`
- Running base command will present you base options:
  - `<base...> creator ...`
  - `<base...> post ...`
  - `<base...> config ...`
- Kemono ripper uses local config file to store its settings so the first thing you have to do is create basic config:
  - `<base...> config create`
- Now you have a `settings.json` file sitting inside app base folder. You can modify it as you wish manually or using `<base...> config modify` command. These settings will be automatically picked at app launch. Any extra options you provide in subsequent non-`config` commands will override default settings (but won't be saved)
- It is recommended to adjust these settings before proceeding (base download folder in particular)
##### Examples
- Dump a list of all creators:
  - `<base...> creator dump`. Use `--prune` flag to save only minimal amount of information required to identify an artist
- List creators by name pattern (case-insensitive):
  - `<base...> creator list xavi`. Output:
    ```ini
    Xavier Houssin: 8868062136923 
    alexavilaavila avila: 79307814
    Noxavious: 66094801
    Xavius: 9650934257100
    ...
    ```
- List creator's posts:
  - `<base...> post list 2479556639713 --service gumroad`. Output:
    ```
    <api_base>/gumroad/user/2479556639713/post/nFYPl
    <api_base>/gumroad/user/2479556639713/post/ZrffZ
    <api_base>/gumroad/user/2479556639713/post/manhr
    ...
    ```
- Download a single post:
  - `<base...> post rip id nFYPl --service gumroad`. Output:
    ```
    ...
    [2479556639713:nFYPl] 'Chamfer Fillet Test.stl': Completed, .../2479556639713/nFYPl/02_Chamfer Fillet Test.stl, size: 0.02 MB
    [queue] post [2479556639713:nFYPl] 'Fillet and Chamfer 3D Printing Test': Done: 3 links: 2 downloaded, 0 failed, 0 skipped, 0 filtered out, 0 already exists, 0 not found, 1 unsupported
    ```
    _Unsupported here is a youtube link_
  - You can also rip posts using full URL `post rip url ...` or even read rip targets from a text file `post rip file`
- Download **all** creator posts
  - `<base...> creator rip 2479556639713 --service gumroad`. Warning: ripper will not check if you have enough free storage space or not!

For bug reports, questions and feature requests use our [issue tracker](https://github.com/trickerer01/kemono-ripper/issues)
