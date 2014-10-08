# Transparent Squid in a container

This is a trivial Dockerfile to build a proxy container.
It will use the famous Squid proxy, configured to work in transparent mode.


## Why?

If you build a lot of containers, and have a not-so-fast internet link,
you might be spending a lot of time waiting for packages to download.
It would be nice if all those downloads could be automatically cached,
without tweaking your Dockerfiles, right?

Or, maybe your corporate network forbids direct outside access, and require
you to use a proxy. Then you can edit this recipe so that it cascades to the
corporate proxy. Your containers will use the transparent proxy, which itself
will pass along to the corporate proxy.


## How?

```
docker run --net host --privileged jpetazzo/squid-in-a-can
```

That's it. Now all HTTP requests going through your Docker host will be
transparently routed through the proxy running in the container.

Note: it will only affect HTTP traffic on port 80.

Note: traffic originating from the host will not be affected, because
the `PREROUTING` chain is not traversed by packets originating from the
host.

Note: if your Docker host is also a router for other things (e.g. if it
runs various virtual machines, or is a VPN server, etc), those things
will also see their HTTP traffic routed through the proxy. They have to
use internal IP addresses, though.

Note: if you plan to run this on EC2 (or any kind of infrastructure
where the machine has an internal IP address), you should probably
tweak the ACLs, or make sure that outside machines cannot access ports
3128 and 3129 on your host.

Note: It will be available to as a proxy on port 3128 on your local machine
if you would like to setup local proxies yourself.


## What?

The `jpetazzo/squid-in-a-can` container runs a really basic Squid3 proxy.
Rather than writing my own configuration file, I patch the default Debian
configuration. The main thing is to enable `intercept` on another port
(here, 3129). To update the iptables for the intercept the command needs
the --privileged flag.

Then, this container should be started using *the network namespace of the
host* (that's what the `--net host` option is for).
Another strategy would be to start the container with its own namespace.
Then, the HTTP traffic can be directed to it with a `DNAT` rule.
The problem with this approach, is that Squid will "see" the traffic as
being directed to its own IP address, instead of the destination HTTP
server IP address; and since Squid 3.3, it refuses to honor such requests.

(The reasoning is, that it would then have to trust the HTTP `Host:`
header to know where to send the request. You can check [CVE-2009-0801]
for details.)


## Tuning

The docker image can be tuned using environment variables.

### MAX_CACHE_OBJECT

Squid has a maximum object cache size. Often when caching debian packages vs
standard web content it is valuable to increase this size. Use the
`-e MAX_CACHE_OBJECT=1024` to set the max object size (in MB)


### DISK_CACHE_SIZE

The squid disk cache size can be tuned. use
`-e DISK_CACHE_SIZE=5000` to set the disk cache size (in MB)

### Persistent Cache

Being docker when the instance exits the cached content immediately goes away
when the instance stops. To avoid this you can use a mounted volume. The cache
location is `/var/cache/squid3` so if you mount that as a volume you can get
persistent caching. Use `-v /home/user/persistent_squid_cache:/var/squid3/cache`
in your command line to enable persistent caching.

## Notes

Ideas for improvement:

- easy chaining to an upstream proxy


[CVE-2009-0801]: http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2009-0801
