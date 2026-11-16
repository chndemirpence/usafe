# USAFE Connect privacy and network behaviour

Maintainer: Cihan Demirpençe, USAFE / ArgoDelta. Updated 16 November 2026.
Questions: ussstarfairy@gmail.com.

## Windows desktop application

USAFE Connect establishes a Tor session when the user selects Connect. Official
Tor components communicate with bridges, transport infrastructure and the Tor
network. The controller verifies the route by requesting
`https://check.torproject.org/api/ip` through the managed SOCKS connection, with
remote DNS. Failed route verification does not trigger a direct-network retry.

The connection applies to the Tor Browser launched by the controller. Opening
that browser contacts the Tor check page and the USAFE website, then the sites
the user chooses. Those services receive requests through the selected route
and have their own policies. See https://www.torproject.org/about/privacy/.

The controller has no automatic telemetry upload or account requirement. Bridge
configuration and Tor session files are processed locally. Connection attempts
are held in memory, capped at ten. The optional connection summary is shown for
review before saving; it contains fixed-choice results and optional feedback,
not bridge addresses, browsing URLs or IP addresses. Saving a summary does not
send it to the maintainer. Users choose whether to share an exported file.

The optional website-launch setting registers a local Windows URI handler after
the user enables it. It allows the site's Open Windows app button to open the
controller; the URI does not supply executable arguments to the connection.

## Browser toolkit

The related USAFE web toolkit processes file cleaning, message/file encryption
and link-tracking removal in the browser. These processing features do not
upload the selected files or plaintext to a USAFE processing server. The cleaner
uses a same-origin content security policy and bundled processing libraries.

Network diagnostics are different: IP lookup, DNS and access tests contact the
listed public services or tested sites. Opening the dashboard can request public
IP information. Browser fingerprint calculations use locally available browser
properties. Site hosting still handles normal page requests; visiting a hosted
tool is not the same as making no network requests. Local preferences and offline
application assets may be stored by the browser and can be cleared in its site
data settings.

## Updates and support

Public Windows 0.1.2 does not automatically download controller updates. The
new update component in source requires an explicit check, a configured trust
root and a chosen network route. It is not yet enabled in the public app.
Build-machine release checks and signing are maintainer operations.

GitHub processes source/release-download requests under its own privacy policy:
https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement.
If a user emails support or submits a signing application, the message and
contact details are processed by the relevant mail/form provider and recipient.
No connection report is attached automatically.
