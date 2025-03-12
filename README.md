# AceList ↔

Matches an AceStream playlist with an XMLTV file.

## Table Of Contents 📖

- [Features ⚡](#features-)
- [Usage 🧑‍🏭](#usage-)
  - [Advanced Features 🔩](#advanced-features-)
    - [Customizable Backend 🚅](#customizable-backend-)
    - [Periodic Updates ⏱](#periodic-updates-)
    - [CutOff - or adjusting the matching confidence 🧭](#cutoff---or-adjusting-the-matching-confidence-)
    - [Cleaning Up The Playlist Names 🧹](#cleaning-up-the-playlist-names-)
    - [Local Mode 💻](#local-mode-)
  - [xTeVe / Threadfin Integration ⚒](#xteve--threadfin-integration-)
- [Motivation 🎭](#motivation-)
- [License 🔓](#license-)

## Features ⚡

* ↔ **Mapping** between a M3U8 playlist and an XMLTV files.
  * 📐 **Adjustable** cutoff of the mapping.
  * 🚫 **Arbitrary clean-up list** to optimize even more the matching.
  * ✅ **Automatic ID Assignment**, so your playlist always matches a XMLTV channel.
* ⏰ **Scheduled** update of the remote playlist and XMLTV sources.
* ⛱ **Flexible** output generation, changing the remote host, port, and more!
* 🚀 **Fast and asynchronous** thanks to FastAPI.

## Usage 🧑‍🏭

The tool has several of parameters to be fully customizable, but only two
are required: the playlist and the XMLTV file.

> AceList is designed to work as a daemon, on environments that
> access both remote playlist and XMLTV files. There is no local mode
> at this moment.

Let's say you have a playlist located at `http://localhost:9090/playlist.m3u8`
and an XMLTV guide placed at `http://localhost:9090/guide.xml`. Running
AceList is as simple as:

```shell
acelist --playlist-url http://localhost:9090/playlist.m3u8 --xmltv-url http://localhost:9090/guide.xml
```

That will:

1. Launch the AceList server on `localhost:8080`.
2. Match the given playlist with the XMLTV channels.
3. Periodically - every 30 seconds - update the playlist and channels.

Now, if you go to `http://localhost:8080/playlist` you will get the mapped
playlist with only the matching channels! Cool, right? 😎

### Advanced Features 🔩

#### Customizable Backend 🚅

Now, what happens if your remote playlist has **lots of streams** but the
AceStream backend does not match yours? For example, the remote playlist
maps to `https://1234:6878` for some channels, `http://localhost:8123` for
others, etc.

Well, AceList gets you covered 🛡! The `/playlist` endpoint **is customizable**
and accepts several arguments:

- `scheme`, so you can modify and set `http`, `https`, or whatever you need!
- `host` to match your backend host.
- `port` to modify the backend port.
- `unique_id` to generate unique stream IDs per stream.

This way, a valid request may look like:

```console
$ curl -q "http://localhost:8080/playlist?scheme=http&host=localhost&port=1111&unique_id=false"
#EXTM3U
#EXTINF:-1 tvg-id="My mapped channel",My Mapped Channel HD
http://localhost:1111/ace/getstream?id=abcdefg
```

> **Tip 🪙**: The parameters can vary and get updated. If you directly
> access `/` or `/docs` when AceList is running, you will see all the
> available parameters:
>
> ![AceList documentation page](/docs/img/acelist-docs.png)

#### Periodic Updates ⏱

If your remote playlist or channel gets updated with a known frequency,
or you want to have it updated to match any new playlist/channel, you can
change the update frequency.

The AceList has a parameter `--interval` where you can set, in seconds, how
frequently you want the playlist and XMLTV files to be synchronized. By
default, it is set to **30 seconds**.

Changing the interval will affect:

* The potential downtime, as when the playlist is being updated, requests
  may be blocked.
* The usage and how frequently the playlist is updated.

#### CutOff - or adjusting the matching confidence 🧭

The cutoff refers to the confidence of the model that matches the playlist
and its channels. It is a floating-point value **within the range `[0, 1]`**
where `0` will match **every channel** and `1` will look for **exact matches**. It is expressed in terms of percentage.

By default, the cutoff value is set to `0.95` which translates into a
*confidence of 95%* or a *failure rate of 5%*. To make a more visual
example:

```
Cut Off:                0.75 (75%)
Playlist Channel name:  A TV Channel HD
XMLTV Channel name:     A TV Channel
Match:                  ✅
------------------------------------------
Cut Off:                0.75 (75%)
Playlist Channel name:  Another TV Channel
XMLTV Channel name:     A TV Channel
Match:                  ✅
------------------------------------------
Cut Off:                0.95 (95%)
Playlist Channel name:  A TV Channel HD
XMLTV Channel name:     A TV Channel
Match:                  ❌
------------------------------------------
Cut Off:                0.95 (95%)
Playlist Channel name:  Another TV Channel
XMLTV Channel name:     A TV Channel
Match:                  ❌
```

Looking at the example above, you may think: Why not going to the `0.75`
cutoff? That **completely depends on your needs**. It's always better to
go with a higher cutoff value and play with `--cleanup-re` option to
tweak and adjust the namings.

#### Cleaning Up The Playlist Names 🧹

The situation above is quite common, mostly if you use externally-managed
playlists. Sometimes the names are mostly correct but they have some
"extras" that add information to the title but it's useless when matching
the corresponding XMLTV channel.

AceList supports an arbitrary list of **regular expressions** where you
can put what you want to remove.

> **Tip 🪙**: Here you have the https://regex101.com/ page, quite handy when
> testing your regular expressions.

For the example above, you can just add to the AceList command the following
argument to remove the `HD` from every channel: `--cleanup-re HD`:

```
Cleanup Re:             HD
Cut Off:                0.95 (95%)
Playlist Channel name:  A TV Channel HD
XMLTV Channel name:     A TV Channel
Match:                  ✅
------------------------------------------
Cleanup Re:             HD
Cut Off:                0.95 (95%)
Playlist Channel name:  Another TV Channel
XMLTV Channel name:     A TV Channel
Match:                  ❌
```

You can build regular expressions as complex as you want. Here I give you
some useful ones:

* `\(.*\)`: remove any structure that has parenthesis, optionally with 
contents inside.
* `(HD|FHD|QHD|SD)`: remove any of `HD`, `FHD`, `QHD`, or `SD` from the name.

> **Note 📝**: The `--cleanup-re` can be placed multiple times, making it
> easier to you to have several regular expressions at the same time.

#### Local Mode 💻

Although AceList is meant to be run as a web server, it can be run locally
to generate a M3U8 playlist in a one-shot run.

All the parameters that are available through the web can be set through
the CLI, by using the `--scheme`, `--host`, `--port`, `--cutoff`, and
`--unique-id`.
Those options are only available when adding the `--output` modifier.

### xTeVe / Threadfin Integration ⚒

Integrating AceList with xTeVe / Threadfin is quite easy! The coolest thing
is that it gives you automatic updates without any intervention.

Once you have AceList running, head yourself to the xTeVe / Threadfin main
page, and add a new playlist. In the pop-up menu, just fill all the details
and settings you need:

![Threadfin playlist pop-up menu](/docs/img/xteve-playlist.png)

The configuration above will:

* Set the scheme to `http`.
* Set the remote host to `localhost`.
* Set the remote port to `8080`.

> **Tip 🪙**: Are you curious why AceStream is on port `8080` instead of `6878`?
> Check my other project [Acexy](https://github.com/Javinator9889/acexy),
> an AceStream proxy server!

Let xTeVe / Threadfin update the playlist, and go to the `XMLTV` tab. There,
put **exactly the same XMLTV** as the one you used in AceList. Let it run
and sync, and... MAGIC 🪄!!

If you head yourself to the `Mapping` tab, you will see all of your channels
**already mapped** with nothing else to do from your side! Just configure
whatever application you use to visualize the streams and enjoy.

## Motivation 🎭

There are **several, open channels** that publish their information to the
web using the XMLTV file. Additionally, they also have **open IPTV streams** 
accessible, but joining them is usually a pain.

The shared playlist tends to be giant, with not-so-useful names that need to
be mapped manually.

Instead, I decided to write my **own mapper** which intelligently joins
an arbitrary playlist with an XMLTV file.

## License 🔓

```
AceList  Copyright (C) 2025  Javinator9889
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions.
```
