param([string]$Out="data/sources",[string]$Disc="0",[int]$MinLen=1200)
& makemkvcon.exe mkv "disc:$Disc" all $Out --minlength=$MinLen --progress=-stdout
