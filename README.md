# WinColl

https://github.com/rrthomas/wincoll  

by Reuben Thomas <rrt@sc3d.org>  

WinColl is a simple puzzle game in which you tunnel through caverns
collecting diamonds while avoiding being squashed by falling rocks. It is
based on [Repton](https://en.wikipedia.org/wiki/Repton_(video_game)) (but
without eggs and monsters).

I originally wrote WinColl for Acorn RISC OS. Original and updated [RISC OS
versions](<https://github.com/rrthomas/wincoll/RISC OS.md>) are available.

The name of the game is an abbreviation of my school’s. “Repton” is also the
name of a school, but I don’t believe the game was named after it!


## Credits

Paul Smith designed the title graphics, and Alistair Turnbull helped with
the game graphics.

Level design by Alistair Turnbull, Paul Smith, Jeremy Douglas, Paul Wilson
and Daniel Thomas.

The sounds are from [Freesound](https://freesound.org), lightly adapted.


## Installation and use
 
The game provides instructions on how to play.

### Binary installers

Installers are available for GNU/Linux, macOS and Windows. See the
[latest release](https://github.com/wincoll/releases):

* The GNU/Linux version is a single binary; you need to make it executable
  and then either copy it to a directory on your path, or run it directly:
  `chmod +x NAME-OF-FILE; ./NAME-OF-FILE`
* The macOS version is a disk image file containing an application. Drag the
  application to a suitable location (e.g. your Applications folder). macOS
  will probably refuse to run it until you have approved it in System
  Settings→Privacy and Security, under “Security”.
* The Windows version is a single `.exe`. Unfortunately it is detected as a
  virus by most virus scanners, including Microsoft Defender, because Python
  apps have often been used to distribute malware. Hence, you will probably
  have to turn off virus scanning before you download it (to prevent it from
  being immediately quarantined or deleted), and then add an exception for
  it. After that, you can put the `.exe` file in a suitable location and
  double-click it to play.

### Python package

If you are a Python user, this is the simplest way to get WinColl on most
machines.

Install with `pip`: `pip install wincoll`, then execute the command
`wincoll`.


## Creating and editing levels

Currently, to play edited or new levels you must have a source check-out of
WinColl from GitHub. (If this doesn’t make sense to you, sorry! I hope to
provide a simpler way to edit and play new levels soon.)

The level files are in the `wincoll/levels` subdirectory of the project, and
are [Tiled](https://www.mapeditor.org/) level editor files, so you will need
to install Tiled to edit them or create new levels.

Having saved an edited level you can install the Python package with
`pip install .` or run it directly with `PYTHONPATH=. python -m wincoll`.

Some notes about level design:

+ A set of levels is numbered according to the lexical order of their file
  names.
+ The supplied levels have a brick wall all the way around. This is
  conventional but not necessary: there’s an imaginary brick wall around the
  outside of the level already.
+ Levels need exactly one start position, given by placing the Win
  character.
+ No checks are done to make sure a level is possible to complete; for
  example, you can place diamonds surrounded by bricks, or have safes but no
  key.
+ A complete level set requires a Tiled tileset and corresponding graphics.
  You can simply copy the tileset file `WinColl.tsx` and PNG graphics from
  `wincoll/levels`.

I welcome [pull requests](https://github.com/rrthomas/wincoll/pulls) for new
levels.


## Improving WinColl

New levels, usability improvements and translations are welcome, as are
usability improvements: for example, the ability to rebind keys would be
welcome.

Some levels useful for testing are in `test-levels`.


## Copyright and Disclaimer

WinColl is distributed under the GNU Public License version 3, or, at your
option, any later version. See the file COPYING.

THIS PROGRAM IS PROVIDED AS IS, WITH NO WARRANTY. USE IS AT THE USER'S RISK.
WinColl’s code is copyright Reuben Thomas, and its levels and graphics by
Reuben Thomas, Alistair Turnbull, Paul Smith and Jeremy Douglas.

The font “Acorn Mode 1”, which is based on the design of Acorn computers’
system font, as used on the Acorn Archimedes on which WinColl was originally
written, is by p1.mark and Reuben Thomas and licensed under CC BY-SA 3.0.

The sound effects are copyrighted and licensed as follows:

+ Diamond collection:
  [Ding.wav by datasoundsample](https://freesound.org/s/638638/) under CC
  BY 4.0
+ Rock fall:
  [WHITE_NOISE-10s.wav by newagesoup](https://freesound.org/s/349315/)
  under CC 0
+ Safe unlock:
  [Old Church Bell (no noise) by igroglaz](https://freesound.org/s/633208/)
  under CC 0
+ Death splat:
  [Splat1.wav by Shakedown_M](https://freesound.org/s/685205/) under CC 0
