<!-- BEGIN AUTO-GENERATED HEADER -->

[![Release](https://img.shields.io/github/v/release/natekspencer/ha-planta?style=for-the-badge)](https://github.com/natekspencer/ha-planta/releases)
[![HACS Badge](https://img.shields.io/badge/HACS-default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Buy Me A Coffee/Beer](https://img.shields.io/badge/Buy_Me_A_☕/🍺-F16061?style=for-the-badge&logo=ko-fi&logoColor=white&labelColor=grey)](https://ko-fi.com/natekspencer)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor_💜-6f42c1?style=for-the-badge&logo=github&labelColor=grey)](https://github.com/sponsors/natekspencer)

![Downloads](https://img.shields.io/github/downloads/natekspencer/ha-planta/total?style=flat-square)
![Latest Downloads](https://img.shields.io/github/downloads/natekspencer/ha-planta/latest/total?style=flat-square)

<!-- END AUTO-GENERATED HEADER -->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="custom_components/planta/brand/dark_logo.png">
  <img alt="Planta logo" src="custom_components/planta/brand/logo.png">
</picture>

# Planta for Home Assistant

Integrate the Planta plant care app with Home Assistant to sync your plant data and unlock powerful automations and insights.

Keep track of watering, fertilizing, and more - and even flash a smart light when your Monstera needs some love! 🌿

_Note_: A Planta premium subscription is required to access the API features used by this integration.

<!-- BEGIN AUTO-GENERATED INSTALLATION -->

## ⬇️ Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=natekspencer&repository=ha-planta&category=integration)

This integration is available in the default [HACS](https://hacs.xyz/) repository.

1. Use the **My Home Assistant** badge above, or from within Home Assistant, click on **HACS**
2. Search for `Planta` and click on the appropriate repository
3. Click **DOWNLOAD**
4. Restart Home Assistant

### Manual

If you prefer manual installation:

1. Download or clone this repository
2. Copy the `custom_components/planta` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

> ⚠️ Manual installation will not provide automatic update notifications. HACS installation is recommended unless you have a specific need.

## ➕ Setup

Once installed, you can set up the integration by clicking on the following badge:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=planta)

Alternatively:

1. Go to [Settings > Devices & services](https://my.home-assistant.io/redirect/integrations/)
2. In the bottom-right corner, select **Add integration**
3. Type `Planta` and select the **Planta** integration
4. Follow the instructions to add the integration to your Home Assistant
<!-- END AUTO-GENERATED INSTALLATION -->

## 🪴 Entities

Each plant is added as a device with the following entities. Entities marked ❌ are still created, but start disabled so they don't record any history. You can enable them individually per plant. Entities without a value when the plant is added also start disabled.

### Plant sensors

| Sensor         | Description                                         | Enabled by default |
| -------------- | --------------------------------------------------- | :----------------: |
| Health         | Plant health, as last reported in the Planta app    |         ❌         |
| Size           | Plant height                                        |         ❌         |
| Growing medium | Soil or other growing medium the plant is potted in |         ❌         |
| Pot size       | Pot diameter                                        |         ❌         |
| Pot type       | Pot material or type                                |         ❌         |
| Site           | Site (room or area) the plant is in                 |         ❌         |

### Care sensors

Care sensors are only created for actions that are scheduled for the plant.

| Action          | Scheduled (date) | Last (timestamp) | Time since last (duration) |
| --------------- | :--------------: | :--------------: | :------------------------: |
| Watering        |        ✅        |        ✅        |             ❌             |
| Fertilizing     |        ✅        |        ❌        |             ❌             |
| Misting         |        ✅        |        ❌        |             ❌             |
| Cleaning        |        ✅        |        ❌        |             ❌             |
| Repotting       |        ✅        |        ❌        |             ❌             |
| Progress update |        ❌        |        ❌        |             ❌             |

Last watering also counts liquid fertilizing.

### Other entities

| Entity                                                        | Description                             | Enabled by default              |
| ------------------------------------------------------------- | --------------------------------------- | ------------------------------- |
| Image                                                         | Plant photo                             | ✅                              |
| Complete watering / fertilizing / misting / cleaning (button) | Marks the action as completed in Planta | ✅ when the action is scheduled |
| Today's tasks (to-do list)                                    | Care tasks due today, across all plants | ✅                              |
| Upcoming tasks (to-do list)                                   | Upcoming care tasks, across all plants  | ✅                              |

## ⚙️ Options

To change which sensors are enabled by default, go to the Planta integration and select **Configure**. Changes apply to plants added afterwards. Turn on **Enable all** to enable every sensor type, including types added in future versions. Select **Apply to existing plants** to also enable or disable the sensors of existing plants to match. Sensors you disabled yourself are left alone, but sensors you enabled yourself are disabled if their type isn't selected.

---

<!-- BEGIN AUTO-GENERATED FOOTER -->

## ❤️ Support Me

While I'm not employed by Planta, I collaborated closely with their team to provide input on the necessary data and structure for this integration and assist with testing to help shape their public API. I’ll continue to work with them to ensure ongoing improvements as needed. That said, I provide this custom component for your enjoyment and home automation needs, as-is, and without guarantees.

If you find it useful, consider supporting development:

- 💜 [Sponsor me on GitHub](https://github.com/sponsors/natekspencer)
- ☕ [Buy me a coffee / beer](https://ko-fi.com/natekspencer)
- 💸 [PayPal (direct support)](https://www.paypal.com/paypalme/natekspencer)
- ⭐ [Star this project](https://github.com/natekspencer/ha-planta)
- 📦 If you’d like to support in other ways, such as donating hardware for testing, feel free to [reach out to me](https://github.com/natekspencer)

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=natekspencer/ha-planta)](https://www.star-history.com/#natekspencer/ha-planta)

<!-- END AUTO-GENERATED FOOTER -->
