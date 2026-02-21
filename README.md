# Breadbox
Breadbox is a REST API for accessing archived media and its metadata.

It supports signed URLs, API keys, users, and a bunch more little things like that.

You can easily add your own archive to your Breadbox by creating a new python file in the `routers` directory and using some of the built-in tools.

My current instance of Breadbox includes archives for anime, manga, games, and linux ISOs.

## Tools
I've created a few tools for interacting with your Breadbox server.

- [Breadbox-Py](https://github.com/ModestBitboard/Breadbox-Python) - Python API with special features
- [Itadakimasu](https://github.com/ModestBitboard/Itadakimasu) - Anime streaming client

## breadctl
Pronounced as "bread control," breadctl is a work-in-progress CLI for Breadbox allowing you to manage users, archives, and routers.

Breadctl is currently being written in Python, but I'm considering porting it to golang and making it its own tool.

Expect this particular feature to change a lot as it gets developed.

## Running in a Container
Breadbox was built with the intention of being run containerized. While it can be run bare-metal, I'd suggest containerization for easy updating and stability.

Some poorly-written directions for containerization exist in [BUILD.md](BUILD.md)

## Support
If you liked this project, go ahead and give it a star. And if you really ***really*** like it, consider sending me a tip.

> **BTC**: `bc1q8tmwuyxpgkuptwu3mn4ryaemp3umvwcc0e5nkk`
