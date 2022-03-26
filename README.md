![GitHub release (latest by date)](https://img.shields.io/github/v/release/v411e/ovgumensabot)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/v411e/ovgumensabot/CI?label=maubot%20package%20build)
![Matrix Bot Profile](https://img.shields.io/badge/matrix-%40mensabot%3Avalentinriess.com-blueviolet)
# OvGU Mensa Bot (matrix)
A [maubot](https://github.com/maubot) bot for the canteen at Otto-von-Guericke-Universität Magdeburg.

## Setup
- Load the *.mbp file into your Maubot Manager
- Create client and instance in Maubot Manager

## Commands
- `!hunger`: Get the menu (before 14:00 - today // after 14:00 - next available day)
  - Combine with keyword to query specific day (e.g. `!hunger monday` or `!hunger 01.04.2042`):
    - `today`
    - `tomorrow`
    - `dd.mm.yyyy`
    - `monday`
    - `tuesday`
    - `wednesday`
    - ...
  - Combine with `fetch` to update internal cache (e.g. `!hunger fetch` or `!hunger fetch tomorrow`)
- `!subscribe` Enable notifications for the menu on the next day
- `!unsubscribe` Disable notifications for the menu on the next day