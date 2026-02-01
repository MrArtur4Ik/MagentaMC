import main, server, os, configparser, logging, subprocess, threading

if __name__ == "__main__":
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    parser = configparser.ConfigParser()
    server.config = parser

    #loading main config
    if os.path.exists(server.config_file):
        parser.read(server.config_file)
    else:
        parser.add_section("Server")
        parser["Server"]["port"] = "25565"
        parser["Server"]["max-players"] = "10"
        parser.add_section("OnlineMode")
        parser["OnlineMode"]["public"] = "false"
        parser["OnlineMode"]["player-verify"] = "true"
        parser["OnlineMode"]["display-name"] = "A Minecraft server."
        parser["OnlineMode"]["software"] = "MagentaMC"
        with open(server.config_file, "w") as file:
            parser.write(file)
    
    #loading administration (operators) list
    if os.path.exists(server.ops_file):
        with open(server.ops_file) as file:
            line = file.readline()
            while line:
                server.ops.append(line.strip())
                line = file.readline()
    else:
        with open(server.ops_file, "w") as file: pass
    
    def update_git_version():
        try:
            server.git_version = subprocess.check_output(["git", "describe", "--always"]).strip().decode()
        except:
            pass
    
    threading.Thread(target=update_git_version).run()
    
    server.port = int(parser["Server"]["port"])
    server.max_players = int(parser["Server"]["max-players"])
    if parser["OnlineMode"]["public"] == "true": server.heartbeat_running = True
    main.main()