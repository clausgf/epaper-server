Epaper Display with ESP32 and Linux Server
==========================================

Overview
--------

The Github repositories [epaper-esp32](https://github.com/clausgf/epaper-esp32) and [epaper-server](https://github.com/clausgf/epaper-server) comprise a complete epaper system, consisting of a configurable and easily extensible server which renders PNG images and an ESP32 based client which displays these images on an epaper panel. Many of the popular Waveshare epaper displays should be supported through the widely used [GxEPD2 library](https://github.com/ZinggJM/GxEPD2).

![](doc/epaper-400x300.png)

I use this project for my personal epaper displays at home and in my office based on the [4.2" 400x300 bw](https://www.waveshare.com/4.2inch-e-Paper.htm) and the [7.5" 880x528 bwr](https://www.waveshare.com/wiki/7.5inch_HD_e-Paper_HAT_(B)) raw panels, but larger deployments with different panels should also work.

The dockerized server can run on any Linux box like Raspberry Pi. It's written in Python/FastAPI and easily adaptable when the configuration options are not sufficient. Currently, there is support for OpenWeather data sources and for extracting information from arbitrary web sites. This information can be displayed in different ways using widgets.

For the epaper client, I use the [Waveshare E-Paper ESP32 Driver Board](https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board) with an AA size LiPo battery in a 3D printed case. For better battery life, the linear regulator on the driver board was replaced by an MCP1700 or an HT7833 in the solder friendly TO-92 package. The MCP1700 is not really recommended as it causes brownout stability problems. Despite a large capacitor, this was observed only during development with USB attached and. It is due to the high current spikes of the ESP32 when using WiFi.

The communication between the client and the server is based on HTTP. To conserve battery life, each request contains an HTTP [If-None-Match header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match) containing the version identifier of the image currently displayed. If the server image is still the same, the server just answers with the *304 Not Modified* http status code. If the image has changed, the server answers with a full response containing the updated PNG image and the *200 OK* HTTP status code. Both anwers contain the (new) version identifier in the `Etag` HTTP header and the time until the client should ask for an update again in the `Cache-Control: max-age=` HTTP header.


Epaper-Esp32
------------

### Installation

1. Get [PlatformIO](https://platformio.org) if you haven't yet. I love the Visual Studio Code integration.
2. Adapt `src/settings.h` based on `src/settings-template.h`.

Epaper-Server
-------------

This is a companion to the epaper display driver [epaper-esp32](https://github.com/clausgf/epaper-esp32) project. Realized as a FastAPI based web server running in a docker container, it provides images and management for epaper displays.

Images for the epaper displays are automatically updated. They can be freely configured with contents from the web. In addition to weather information which can be displayed in various forms, rendering of information collected from arbitrary web pages is supported. Together with epaper-esp32, this project forms a complete epaper display solution.


### Installation

1. Create a `config.yml` file based on the template.
   - define at least one display and arbitrary number of aliases - the client can query the display contents using the display name or any alias
   - You need a free [OpenWeather API key](https://home.openweathermap.org/users/sign_up) for the `Weather` datas source.
   - Use the `WebScraper` data source to extract arbitrary information from web sources based on regular expressions. This should be quite flexible.
   - available widgets include `Date`, `Text` and `WeatherNow`, `WeatherForecast` and `WeatherTemperature`
2. Review `docker-compse.yml`.
   - Redis-Commander should be activated only for debugging and in isolated, private networks. Deactivate it by commenting out the section.
   - The project works nicely in a private network. For use in public networks, appropriate authentication and encrpytion shall be added.
3. Start the service using `docker-compose up -d`.
   - `docker-compose logs` shows logs
   - `docker-compose down`stops the service
4. It shouldn't be too difficult to add custom widgets. Don't forget to add them to `backend/core/widgets/__init__.py`.


### Technical notes

By default, epaper-server supports these endpoints:
- http://localhost:9830/docs OpenAPI/Swagger API docs
- http://localhost:9830/api/displays and links therein: List of displays and display aliases, info about specific displays, and rendered PNG images.
- Optional redis-commander for debugging, http://localhost:9831 (not for production)


Todos
-----
Interesting extension might include (pull requests welcome!):
- Calendar widgets and data sources - Exchange and iCloud calendars might be useful for me!
- Traffic jam / travel time overview using Google Maps (the ugomeda project has one, but that impacts neither me nor my bike :-)
- Some form of device management for the ESP32 fleet (any ideas?)
- Web frontend for some form of management
  - current image/image shown
  - device status


Credits
-------
- This project is strongly inspired by https://github.com/ugomeda/esp32-epaper-display by github user ugomeda.
- SVG weather icons are from https://github.com/erikflowers/weather-icons, PNG conversion from the https://github.com/ugomeda/esp32-epaper-display project
- Further references are found in the source code.
