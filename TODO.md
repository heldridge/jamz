# TODO

You should be able to define *fallback* tags, and more complex templating 
(e.g. is there an *album side*? If so, want to sort correctly)

Also need normalization for characters. See e.g. octopus projectr black blizzard/red upbrella that needs escaping

- check if mapping multiple files with different release-ids to the same folder. Don't want all Weezer self-titled albums to go to the same folder
    - require a manual album-naming

- check if something is actually a music file
- delete empty folders
- don't output unchanging files
- read formatting from a file
- Work with repeating tracks over different sides
- add optional tracknumber padding length 
    - or auto, pads to largest needed
- When fully moving a directory move other non-music files inside it to the new location
- Write tag additions as *plugins*. That way other people can add their own
- Mac will not rename a dirctory of it is just a capitalization change. Either fix this or give a warning
- Try out tag modifications. Maybe a class for "tags modifier", and then a generic class that just does the "look for keys and move to a normalized place"?

