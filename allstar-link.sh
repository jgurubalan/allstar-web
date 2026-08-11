#!/bin/bash

LOCAL_NODE=68751
TARGET=""

get_nodes() {
    sudo asterisk -rx "rpt nodes $LOCAL_NODE" 2>&1
}

check_target() {
    STATUS=$(get_nodes)

    if echo "$STATUS" | grep -qE "(^|[^0-9])$TARGET([^0-9]|$)"; then
        echo "STATUS: Node $TARGET is CONNECTED."
    else
        echo "STATUS: Node $TARGET is NOT connected."
    fi
}

show_connected_nodes() {
    echo
    echo "======================================================="
    echo "       Nodes Currently Connected to $LOCAL_NODE"
    echo "======================================================="

    STATUS=$(get_nodes)

    if echo "$STATUS" | grep -q "<NONE>"; then
        echo "No nodes currently connected."
    else
        echo "$STATUS"
    fi

    echo "======================================"
}

while true; do

    clear

    echo "======================================"
    echo "       AllStarLink Node Control"
    echo "======================================"
    echo "Local node: $LOCAL_NODE"
    echo

    read -p "Enter target node number (or q to quit): " TARGET

    if [[ "$TARGET" == "q" || "$TARGET" == "Q" ]]; then
        exit 0
    fi

    if ! [[ "$TARGET" =~ ^[0-9]+$ ]]; then
        echo "Invalid node number."
        sleep 2
        continue
    fi

    while true; do

        clear

        echo "======================================"
        echo "       AllStarLink Node Control"
        echo "======================================"
        echo "Local node : $LOCAL_NODE"
        echo "Target node: $TARGET"
        echo

        check_target

        echo
        echo "1) Connect"
        echo "2) Disconnect"
        echo "3) Refresh / Show connected nodes"
        echo "4) Change target node"
        echo "5) Disconnect ALL nodes"
        echo "6) Quit"
        echo

        read -p "Select an option: " OPTION

        case "$OPTION" in

            1)
                echo
                echo "Connecting to node $TARGET..."
                sudo asterisk -rx "rpt cmd $LOCAL_NODE ilink 3 $TARGET"
                sleep 2

                echo
                check_target
                show_connected_nodes

                read -p "Press Enter to return to menu..."
                ;;

            2)
                echo
                echo "Disconnecting node $TARGET..."
                sudo asterisk -rx "rpt cmd $LOCAL_NODE ilink 1 $TARGET"
                sleep 2

                echo
                check_target
                show_connected_nodes

                read -p "Press Enter to return to menu..."
                ;;

            3)
                clear

                echo "======================================"
                echo "       AllStarLink Node Status"
                echo "======================================"
                echo "Local node : $LOCAL_NODE"
                echo "Target node: $TARGET"
                echo

                check_target
                show_connected_nodes

                read -p "Press Enter to return to menu..."
                ;;

            4)
                break
                ;;

            5)
                echo
                echo "WARNING: This will disconnect ALL linked nodes."
                read -p "Are you sure? (y/n): " CONFIRM

                if [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]]; then
                    sudo asterisk -rx "rpt cmd $LOCAL_NODE ilink 6"
                    sleep 2

                    echo
                    echo "All links disconnected."
                    show_connected_nodes
                else
                    echo "Cancelled."
                fi

                read -p "Press Enter to return to menu..."
                ;;

            6)
                exit 0
                ;;

            *)
                echo "Invalid selection."
                sleep 2
                ;;

        esac

    done

done