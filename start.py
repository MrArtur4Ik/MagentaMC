import main, server, os, configparser

if __name__ == "__main__":
    parser = configparser.ConfigParser()
    server.config = parser
    if os.path.exists(server.config_file):
        parser.read(server.config_file)
    else:
        parser.add_section("Server")
        parser["Server"]["port"] = "25565"
        parser["Server"]["max-players"] = "10"
        parser.add_section("OnlineMode")
        parser["OnlineMode"]["public"] = "false"
        parser["OnlineMode"]["player-verify"] = "false"
        parser["OnlineMode"]["display-name"] = "A Minecraft server."
        parser["OnlineMode"]["software"] = "MagentaMC"
        with open(server.config_file, "w") as file:
            parser.write(file)
    server.port = int(parser["Server"]["port"])
    server.max_players = int(parser["Server"]["max-players"])
    if parser["OnlineMode"]["public"] == "true": server.heartbeat_running = True
    main.main()