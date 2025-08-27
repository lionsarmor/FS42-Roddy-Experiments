#!/bin/bash
pkill kiosk-launcher  # stop Electron kiosk
lxsession -s LXDE-pi -e LXDE
