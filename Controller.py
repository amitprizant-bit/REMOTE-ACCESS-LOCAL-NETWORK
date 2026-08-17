import socket
import struct
import threading
import cv2
import numpy as np
from pynput import keyboard, mouse

TARGET_IP = "192.168.1.215"  # TODO: LAPTOP IP
PORT = 65432
SCREEN_PORT = 65433


def receive_screen():
    screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        screen_socket.connect((TARGET_IP, SCREEN_PORT))
        print("[*] Screen stream connected!")
    except Exception as e:
        print(f"Failed to connect to screen server: {e}")
        return

    # Helper function to read exact block sizes from a TCP stream
    def recv_all(sock, size):
        data = b""
        while len(data) < size:
            packet = sock.recv(size - len(data))
            if not packet:
                return None
            data += packet
        return data

    try:
        while True:
            # 1. Read the 4-byte size header
            size_header = recv_all(screen_socket, 4)
            if not size_header:
                break
            size = struct.unpack("!L", size_header)[0]

            # 2. Read the image payload
            img_data = recv_all(screen_socket, size)
            if not img_data:
                break

            # 3. Decode and display
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow("Remote Desktop Feed", frame)

            # Press 'q' on the image window to close the screen stream
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except Exception as e:
        print(f"Screen receiver error: {e}")
    finally:
        cv2.destroyAllWindows()
        screen_socket.close()


def start_input_sender():
    input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        input_socket.connect((TARGET_IP, PORT))
        print("[*] Input streaming connected!")
    except Exception as e:
        print(f"Failed to connect to input server: {e}")
        return

    # Mouse Listeners
    def on_move(x, y):
        try:
            # Matches target format: "M,move,x,y"
            input_socket.sendall(f"M,move,{x},{y}\n".encode("utf-8"))
        except Exception:
            return False  # Stops listener if socket dies

    def on_click(x, y, button, pressed):
        if pressed:
            try:
                btn_name = "left" if button == mouse.Button.left else "right"
                # Matches target format: "M,click,x,y,button"
                input_socket.sendall(f"M,click,{x},{y},{btn_name}\n".encode("utf-8"))
            except Exception:
                return False

    # Keyboard Listener
    def on_press(key):
        try:
            if hasattr(key, "char") and key.char is not None:
                val = key.char
            else:
                val = key.name  # Special keys like 'enter', 'space'

            # Matches target format: "K,key_press,val"
            input_socket.sendall(f"K,key_press,{val}\n".encode("utf-8"))
        except Exception:
            return False

    # Start pynput listeners
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    # Join keeps the main thread alive running the input loops
    mouse_listener.join()
    keyboard_listener.join()


if __name__ == "__main__":
    # Start the screen receiver thread in the background
    screen_thread = threading.Thread(target=receive_screen, daemon=True)
    screen_thread.start()

    # Run the input sender on the main thread
    start_input_sender()
