#!/usr/bin/osascript

-- first argument is folder of music to add, second argument is playlist to name

on run argv
  set folder_alias to POSIX file (item 1 of argv)
  set playlist_alias to (item 2 of argv)  
  tell application "Music"

    -- make new playlist if not already exists
    if not (user playlist playlist_alias exists) then
      make new user playlist with properties {name:playlist_alias}
    end if

    -- add tracks from given folder to playlist
    add folder_alias to user playlist playlist_alias

  end tell
end run
