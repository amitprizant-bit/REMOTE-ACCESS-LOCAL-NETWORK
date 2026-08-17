import socket
import threading
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import cv2
import mss
import numpy as np
import struct


def handle_inputs():
    try:
        HOST = "0.0.0.0"
        PORT = 65432

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)

        print(f"Server listening on {HOST}:{PORT}")

        conn, addr = server_socket.accept()
        print(f"Connection established with {addr}")

        mouse_controller = MouseController()
        keyboard_controller = KeyboardController()

        while True:
            data = conn.recv(1024).decode("utf-8")
            if not data:
                break
            data_parts = data.split("\n")
            for command in data_parts:
                if not command:
                    continue
                parts = command.split(",")
                device_type = parts[0]
                if device_type == "M":
                    action = parts[1]
                    if action == "move":
                        x, y = int(parts[2]), int(parts[3])
                        mouse_controller.position = (x, y)
                    elif action == "click":
                        x, y = int(parts[2]), int(parts[3])
                        button = Button.left if parts[4] == "left" else Button.right
                        mouse_controller.position = (x, y)
                        mouse_controller.click(button)
                if device_type == "K":
                    action = parts[1]
                    if action == "key_press":
                        key_value = parts[2]
                        if len(key_value) == 1:
                            keyboard_controller.press(key_value)
                            keyboard_controller.release(key_value)
                        else:
                            try:
                                key = getattr(Key, key_value)
                                keyboard_controller.press(key)
                                keyboard_controller.release(key)
                            except AttributeError:
                                print(f"Unknown key: {key_value}")
    except Exception as e:
        print(f"Input error: {e}")
    finally:
        conn.close()
        server_socket.close()


def handle_screen_stream():
    SCREEN_PORT = 65433
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", SCREEN_PORT))
    server_socket.listen(1)
    print(f"Screen stream server listening on {SCREEN_PORT}")

    conn, addr = server_socket.accept()
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        try:
            while True:
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
                result, encoded_frame = cv2.imencode(".jpg", frame, encode_param)
                if not result:
                    continue
                data = encoded_frame.tobytes()
                size = len(data)
                conn.sendall(struct.pack("!L", size) + data)
        except Exception as e:
            print(f"Screen stream error: {e}")
        finally:
            if "conn" in locals():
                conn.close()
            server_socket.close()


if __name__ == "__main__":
    input_thread = threading.Thread(target=handle_inputs)
    screen_thread = threading.Thread(target=handle_screen_stream)

    input_thread.start()
    screen_thread.start()

    input_thread.join()
    screen_thread.join()
