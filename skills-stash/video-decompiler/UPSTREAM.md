# Where this skill comes from

This folder is the video-decompiler skill by James Dimachkie, copied unchanged from its own repository so it ships in
raea's plugin and installer beside the raea skill.

- Source: https://github.com/JimGHTB12/video-decompiler, folder `skills/video-decompiler`
- Commit: `8589a8e3046573f2196e3009be83bd5dd61927c2` (17 November 2026), plugin version 0.2.2
- Licence: MIT (`LICENSE` here). The fonts, pictures and recorded instruments in `library/` keep their own licences,
  listed in `NOTICE` (the repository's root NOTICE, copied in beside it) and in each worked film's `media/` folder.
- Added here: `NOTICE` (from the source repository's root) and this file.
- Changed here, only `SKILL.md`'s front matter: its `description` is in double quotes, the same words (unquoted, the
  colon in "a finished picture): that is" makes the front matter invalid YAML, which `just check` refuses), and it
  gains this repository's `metadata` (`raea-tested-against`, `raea-verbs`).
- Tested against raea 0.1.7 (macOS arm64, 18 November 2026): `vd doctor --full` made its starter film and a copy of
  the `plusone` worked film, built their sound and drew their moments; the skill refuses a raea older than 0.1.1-rc4.
- Left out: the source repository's tests, docs and demo media, and its own plugin manifests (this repository's
  `skills/.claude-plugin/plugin.json` lists the skill).

## What it runs

Its tools are Python (3.10 or later; it was tested on 3.12) in an environment of its own, `~/.venvs/video-decompiler`,
with numpy, OpenCV (headless, below 5), Pillow and psutil from `requirements.txt`. They run `ffmpeg`, `ffprobe` and
`raea` on your computer, `esbuild` or `bun` for `vd playable`, and `git` only to read a repository's history for
`vd capture` and `vd borrow --for`. None of them reaches the network. They write under `~/.vd` (renders, measures and
reader packs) and in the film folder you give them. `vd profile` reads a Claude Code session transcript on your
computer to say where the time went; what it prints from the transcript has keys, tokens and passwords replaced by
`[redacted]`.

## Updating it

Copy the source repository's `skills/video-decompiler` folder at the new commit over this one, keep `NOTICE` and this
file, update the commit above, run `just ci`, and say in the pull request what changed upstream. The skill isn't in the
plugin directory's edition (`directory/`): that edition carries only Markdown, text, JSON, YAML and pictures, and this
skill's tools are Python.
