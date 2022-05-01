![GitHub release (latest by date)](https://img.shields.io/github/v/release/v411e/ovgumensabot)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/v411e/ovgumensabot/CI?label=maubot%20package%20build)
![Matrix Bot Profile](https://img.shields.io/badge/matrix-%40mensabot%3Akeks.club-blueviolet)
# OvGU Mensa Bot (matrix)
A [maubot](https://github.com/maubot) bot for the canteen at Otto-von-Guericke-Universität Magdeburg.

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
- `!hid` List the next "Hörsaal im Dunkeln" events

## Setup
- Install beautifulsoup4 in your maubot sever environment
  - Dockerfile:
    ````
    FROM dock.mau.dev/maubot/maubot

    RUN pip install beautifulsoup4
    ````
  - docker-compose.yml
    ````yaml
    version: "3.6"
    
    services:
      postgres:
        image: postgres:13.2
        restart: always
        expose:
          - 5432
        volumes:
          - ./pgdata:/var/lib/postgresql/data
        environment:
          - POSTGRES_PASSWORD=
          - POSTGRES_USER=
    
      maubot:
        build:
          dockerfile: ./Dockerfile
          context: .
        container_name: maubot
        image: dock.mau.dev/maubot/maubot
        restart: unless-stopped
        volumes:
        - ./logs/:/var/log/maubot
        - ./data:/data
        ports:
          - 29316:29316
        depends_on:
          - postgres
    ````
- Load the *.mbp file into your Maubot Manager
- Create client and instance in Maubot Manager
