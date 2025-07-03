from network import NetworkManager

if __name__ == "__main__":
    print("Select the topology type:")
    print("1. Simple")
    print("2. Complex")
    choice = input("Enter the number of your choice: ")

    if choice == "1":
        topology_type = "simple"
    elif choice == "2":
        topology_type = "complex"
    else:
        print("[ERROR] Invalid choice. Exiting.")
        exit(1)

    print("Select the link layout:")
    print("1. Ring ")
    print("2. Linear")
    layout_choice = input("Enter the number of your choice: ")

    if layout_choice == "2":
        link_type = "linear"
    else:
        link_type = "ring"  

    network_manager = NetworkManager(topology_type, link_type=link_type)
    network_manager.start_network()