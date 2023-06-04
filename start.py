import main, server, os, configparser

if __name__ == "__main__":
    parser = configparser.ConfigParser()
    if os.path.exists(server.config_file):
        parser.read(server.config_file)
    else:
        parser.add_section("Server")
        parser["Server"]["port"] = "25565"
        with open(server.config_file, "w") as file:
            parser.write(file)
    server.port = int(parser["Server"]["port"])
    main.main()