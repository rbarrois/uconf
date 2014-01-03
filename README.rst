UConf
=======


UConf is a small tool aiming to provide simple handling of configuration files for an heterogeneous
computer set.

Its key concepts are:

- Abstract host-specific config to common features (server, relay, ...)
- Host-specific configuration may range from a single-line change to a whole file rewrite
- Configuration files are modified in place, not in the source - versionned - repository.



Configuring
-----------

You can get started with ``uconf init <source_dir> <target_dir>``.
This will generate the following layout::

    ./<source_dir>
        config
        src/

The ``config`` file is UConf's main entry point. Its content should look like::

    [global]
    ; Install files into the <target_dir> folder.
    target: <target_dir>

    ; Default to parsing the files.
    default-action: parse

    [categories]
    ; Put your category definitions here
    ; Example:
    ; myserv: server
    ; server and slave: not master

    [files]
    ; Add category-file rules
    ; server: ssh/sshd_config
    ; laptop: X11/xorg.conf

    [rules]
    ; Override file rules here
    ; boot/splash_screen: copy
