[![Release](https://img.shields.io/github/v/release/natekspencer/ha-planta?style=for-the-badge)](https://github.com/natekspencer/ha-planta/releases)
[![Buy Me A Coffee/Beer](https://img.shields.io/badge/Buy_Me_A_☕/🍺-F16061?style=for-the-badge&logo=ko-fi&logoColor=white&labelColor=grey)][ko-fi]
[![Sponsor me on GitHub](https://img.shields.io/badge/Sponsor_me_on_GitHub-yellow?style=for-the-badge&logo=githubsponsors&logoColor=white&labelColor=grey)][github-sponsor]
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

![Downloads](https://img.shields.io/github/downloads/natekspencer/ha-planta/total?style=flat-square)
![Latest Downloads](https://img.shields.io/github/downloads/natekspencer/ha-planta/latest/total?style=flat-square)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://brands.home-assistant.io/planta/dark_logo.png">
  <img alt="Planta logo" src="https://brands.home-assistant.io/planta/logo.png">
</picture>

# Planta for Home Assistant

Integrate the Planta plant care app with Home Assistant to sync your plant data and unlock powerful automations and insights.

Keep track of watering, fertilizing, and more — and even flash a smart light when your Monstera needs some love! 🌿

_Note_: A Planta premium subscription is required to access the API features used by this integration.

# Installation

There are two main ways to install this custom component within your Home Assistant instance:

1. Using HACS (see https://hacs.xyz/ for installation instructions if you do not already have it installed):

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=natekspencer&repository=ha-planta&category=integration)
   1. Use the convenient My Home Assistant link above, or, from within Home Assistant, click on the link to **HACS**
   2. Click on **Integrations**
   3. Click on the vertical ellipsis in the top right and select **Custom repositories**
   4. Enter the URL for this repository in the section that says _Add custom repository URL_ and select **Integration** in the _Category_ dropdown list
   5. Click the **ADD** button
   6. Close the _Custom repositories_ window
   7. You should now be able to see the _Planta_ card on the HACS Integrations page. Click on **INSTALL** and proceed with the installation instructions.
   8. Restart your Home Assistant instance and then proceed to the _Configuration_ section below.

2. Manual Installation:
   1. Download or clone this repository
   2. Copy the contents of the folder **custom_components/planta** into the same file structure on your Home Assistant instance
      - An easy way to do this is using the [Samba add-on](https://www.home-assistant.io/getting-started/configuration/#editing-configuration-via-sambawindows-networking), but feel free to do so however you want
   3. Restart your Home Assistant instance and then proceed to the _Configuration_ section below.

While the manual installation above seems like less steps, it's important to note that you will not be able to see updates to this custom component unless you are subscribed to the watch list. You will then have to repeat each step in the process. By using HACS, you'll be able to see that an update is available and easily update the custom component.

# Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=planta)

There is a config flow for this integration. After installing the custom component, use the convenient My Home Assistant link above.

Alternatively:

1. Go to **Configuration**->**Integrations**
2. Click **+ ADD INTEGRATION** to setup a new integration
3. Search for **Planta** and click on it
4. You will be guided through the rest of the setup process via the config flow

---

## Support Me

While I'm not employed by Planta, I collaborated closely with their team to provide input on the necessary data and structure for this integration and assist with testing to help shape their public API. I’ll continue to work with them to ensure ongoing improvements as needed. That said, I provide this custom component for your enjoyment and home automation needs, as-is, and without guarantees.

If you run into any issues, feel free to open an issue on GitHub, and I’ll do my best to assist!

If you found this integration useful and want to donate, consider [sponsoring me on GitHub][github-sponsor] or buying me a coffee ☕ (or beer 🍺) by using the link below:

[![Support me on ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)][ko-fi]

[github-sponsor]: https://github.com/sponsors/natekspencer
[ko-fi]: https://ko-fi.com/natekspencer
