# Build instructions
Unfortunately for some, Breadbox does not work out-of-the-box.
The container ***WILL*** crash and fail unless you follow these instructions.

## Step 1: Create config directory
The Breadbox Dockerfile sets the `/config` directory inside the container to store config file, user database, and SSL certificate.
You will need to mount this container to your main file system in order for Breadbox to function correctly.
I personally use `/usr/share/breadbox`, but `/etc/breadbox` also makes sense. This location is entirely up to you,
just make sure you can easily locate it.

## Step 2: Create archive directory
Breadbox won't start unless it has a place to store it's archives. I use an internal HDD mounted to `/warehouse` in my own setup,
with a directory `/warehouse/archives` for Breadbox archives. I then mount that to `/archives` within the container.

## Step 3: compose.yml
You can instead opt to do this command-line, but since I turned my container into a systemd service I found this easier to work with.

Just remember to mount your config directory to `/config` and your archives to `/archives`, then forward port `80` to whatever port you'd like. For example, `8080:80`.

## Step 4: Run & configure
Once you're satisfied with your setup, I recommend running your Breadbox container once to generate the config file.
You can also opt to instead create it manually, although I'm not going to be able to hold your hand through that process.

Now configure Breadbox by editing the `config.toml` file in the config directory we decided on earlier. You'll see a bunch of values there, but the only ones you need to change right now are `server/port` and `archives`.

First, change the port to `80`.

Now add your archive paths.
This is an example of mine:

```toml
[archives]
Anime = "/archives/anime"
Games = "/archives/games"
```

## Step 5: SSL certificate generation
I've set up Breadbox to use a self-signed certificate in order to protect the API keys from man-in-the-middle attacks.
I HIGHLY recommend you do the same.

In a command line, move into your config directory. For example,
```bash
cd /usr/share/breadbox
```

Next, create a new directory.
```bash
mkdir ssl
```

Now lastly, generate a self-signed certificate.
```bash
openssl req -x509 -newkey rsa:4096 -keyout ./ssl/key.pem -out ./ssl/cert.pem -sha256 -days 3650 -nodes
```

Fill out any questions with whatever info you want. If you own a domain, you can also opt for a certificate signed by a CA so that
it doesn't appear as a security risk to your browser. There are plenty of guides to do this online, just remember to save the
certificate to `.../ssl/cert.pem` and the private key (unencrypted!!) to `.../ssl/key.pem`.

## Step 6: API key setup
You should now be able to run Breadbox containerized! Now, unless you've set read access to everyone, you won't be able to do anything.
You can gain access by generating an admin API key.

You'll either need to access your container's console, or utilize the `users.py` module to edit the `users.db` file in your config directory.

I'm not really smart enough to do a good job at explaining setting up an account. So instead, please read through the `users.py` file for references.
It should be easy enough to use. You'll need to either create a virtual environment an install it's requirements, or enter the container and use the console to do it.

**Make sure to store your API key somewhere safe. Breadbox stores all API keys as Argon2 hashes, so you won't be able to see it again after you generate it!**
