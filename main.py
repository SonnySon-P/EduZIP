import os  # 與作業系統進行互動
import sys  # 處理與Python解釋器相關的設定與操作
import json  # 用來處理JSON格式的資料
import struct  # 用來處理二進位資料與資料型態之間的轉換
import heapq  # 實作資料結構中的堆積
from collections import Counter  # 計數器

class HuffmanNode:
    def __init__(self, byte = None, frequency = 0):
        self.byte = byte  # 儲存實際的資料
        self.frequency = frequency  # 儲存該資料出現的次數
        self.left = None  # 指向左子節點的指標
        self.right = None  # 指向右子節點的指標

    def __lt__(self, other):
        return self.frequency < other.frequency  # 當執行至node1 < node2時，將自動依據節點frequency進行比較，並回傳布林值

def build_huffman_tree(frequency):
    heap = []

    # 每一個字元根據它的頻率變成葉子節點，並丟進堆積
    for byte, freq in frequency.items():
        heapq.heappush(heap, HuffmanNode(byte, freq))

    # 如果整個檔案只有一種字元
    if len(heap) == 1:
        return heap[0]

    # 建立霍夫曼樹
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)

        parent = HuffmanNode(frequency = left.frequency + right.frequency)
        parent.left = left
        parent.right = right

        heapq.heappush(heap, parent)

    return heap[0]

def generate_codes(node, code = "", codes = None):
    # 初始化字典
    if codes is None:
        codes = {}

    # 終止條件
    if node is None:
        return codes

    # 找到葉子節點
    if node.byte is not None:
        if code:
            codes[node.byte] = code
        else:
            codes[node.byte] = "0"

        return codes

    # 遞迴遍歷左、右子樹
    generate_codes(node.left, code + "0", codes)
    generate_codes(node.right, code + "1", codes)

    return codes

def huffman_decompress(encoded_data, frequency, padding):
    # 重建霍夫曼樹
    root = build_huffman_tree(frequency)

    # 將二進位數值還原為霍夫曼編碼
    bit_string = ""

    for byte in encoded_data:
        bit_string += f"{byte:08b}"

    if padding:
        bit_string = bit_string[:-padding]

    # 巡訪霍夫曼樹進行解碼
    decoded = bytearray()

    # 走訪二進位字串
    current = root

    for bit in bit_string:
        if bit == "0":
            current = current.left
        else:
            current = current.right

        if current.byte is not None:
            decoded.append(current.byte)
            current = root

    return bytes(decoded)

def huffman_compress(data):
    # 統計出檔案中，每個字元各出現了幾次
    frequency = Counter(data)

    # 建立霍夫曼樹
    root = build_huffman_tree(frequency)

    # 產生對應的霍夫曼編碼字典
    codes = generate_codes(root)

    # 編碼
    encoded_bits = ""

    for byte in data:
        encoded_bits += codes[byte]

    # 補齊長度
    padding = 8 - (len(encoded_bits) % 8)

    if padding != 8:
        encoded_bits += "0" * padding
    else:
        padding = 0

    # 將霍夫曼編碼真正轉換成二進位數值
    encoded_bytes = bytearray()

    for i in range(0, len(encoded_bits), 8):
        encoded_bytes.append(int(encoded_bits[i : i + 8], 2))

    # 統計每個字元出現的次數
    frequency = dict(Counter(data))

    return bytes(encoded_bytes), frequency, padding

def lz77_decompress(compressed_data):
    decompressed = bytearray()  # 建立一個空的位元組陣列
    position = 0  # 記錄目前處理到壓縮檔案的第幾個位元
    data_length = len(compressed_data)  # 計算壓縮檔案的大小

    # 計算Token大小，固定為4位元組
    token_size = struct.calcsize(">HBB")

    while position < data_length:
        # 讀取一個4位元組的Token
        token = compressed_data[position : position + token_size]
        if len(token) < token_size:
            break

        # 解壓縮Token
        offset, length, next_char = struct.unpack(">HBB", token)

        # 如果有匹配到歷史資料，則從已解壓的資料中複製
        if offset > 0:
            start_index = len(decompressed) - offset
            for i in range(length):
                # 逐字元複製
                decompressed.append(decompressed[start_index + i])

        # 加上Token帶來的下一個新字元
        if position + token_size < data_length or next_char != 0 or length > 0:
            # 只有當不是最後一個無意義的補零, Token時才寫入
            if position + token_size < data_length or next_char != 0:
                decompressed.append(next_char)

        position += token_size

    return bytes(decompressed)

def lz77_compress(data, window_size = 4096, lookahead_buffer_size = 15):
    compressed = bytearray()  # 建立一個空的位元組陣列
    position = 0  # 記錄目前處理到來源檔案的第幾個位元
    data_length = len(data)  # 計算來源檔案的大小

    while position < data_length:
        match_offset = 0
        match_length = 0

        # 定義Search Buffer與Lookahead Buffer
        search_start = max(0, position - window_size)  # 歷史紀錄從哪裡開始搜尋
        lookahead_end = min(data_length, position + lookahead_buffer_size)  # 從當前位置往後數一個緩衝區大小

        # 在搜尋視窗中尋找最長匹配
        for i in range(search_start, position):
            length = 0

            # 比對重複字串
            while (position + length < lookahead_end and i + length < position and data[i + length] == data[position + length]):
                length += 1
                if length == lookahead_buffer_size:
                    break

            # 如果找到更長的匹配，更新記錄
            if length > match_length:
                match_length = length
                match_offset = position - i

        # 處理下一個字元
        if position + match_length < data_length:
            next_char = data[position + match_length]
        else:
            next_char = 0  # 若已到檔案末尾，以0代替

        # 壓縮成二進位的Token格式: H(offset): 2 位元組, B(length): 1 位元組, B(next_char): 1位元組 -> 共4位元組
        token = struct.pack(">HBB", match_offset, match_length, next_char)
        compressed.extend(token)

        # 移動指標
        position += match_length + 1

    return bytes(compressed)

def decompress_files(zip_path, decompress_directory):
    # 檢查來源壓縮檔案是否存在
    if not os.path.exists(zip_path):
        print(f"錯誤: 找不到壓縮檔案 {zip_path}")
        return

    # 自動檢查，並建立目標資料夾
    if not os.path.exists(decompress_directory):
        os.makedirs(decompress_directory)

    # 擷取純檔名，用於終端機提示
    zip_name = os.path.basename(zip_path)

    print(f"開始解壓縮 {zip_name} 到資料夾 {decompress_directory}...")

    # 以二進位唯讀模式開啟壓縮檔
    with open(zip_path, "rb") as input_file:
        # 移到檔案最末尾4個位元組，讀取中央目錄的「起始偏移量」
        input_file.seek(-4, os.SEEK_END)
        end_of_json_pos = input_file.tell()  # 記錄JSON的結束邊界
        directory_offset_bytes = input_file.read(4)
        directory_offset = struct.unpack("I", directory_offset_bytes)[0]

        # 跳到中央目錄的起點，讀取並還原JSON後設資料
        input_file.seek(directory_offset)
        json_length = end_of_json_pos - directory_offset  # 精準計算JSON長度
        directory_json_bytes = input_file.read(json_length)
        central_directory = json.loads(directory_json_bytes.decode("utf-8"))

        current_file_offset = 0

        for meta in central_directory:
            file_name = meta["filename"]
            compressed_size = meta["compressed_size"]
            #file_size = meta["size"]

            # 獲取起始偏移量
            offset = meta.get("offset", current_file_offset)

            # 移動到該檔案數據在打包檔中的真實起點，並讀取對應大小
            input_file.seek(offset)
            compressed_file_data = input_file.read(compressed_size)

            frequency = {
                int(k): v
                for k, v in meta["frequency"].items()
            }

            padding = meta["padding"]

            lz77_data = huffman_decompress(compressed_file_data, frequency, padding)

            file_data = lz77_decompress(lz77_data)

            # 組合出最終解壓縮後的完整路徑
            target_path = os.path.join(decompress_directory, file_name)

            # 將二進位數據還原寫入硬碟
            with open(target_path, "wb") as output_file:
                output_file.write(file_data)

    print("解壓縮檔案完成！")

def compress_files(file_path):
    # 自動生成ZIP檔案路徑
    zip_path = os.path.splitext(file_path)[0] + ".zip"

    central_directory = []

    # 擷取純檔名與副檔名
    file_name = os.path.basename(file_path)
    zip_name = os.path.basename(zip_path)

    print(f"開始將 {file_name} 壓縮至 {zip_name}...")

    # 檢查來源檔案是否存在
    if not os.path.exists(file_path):
        print(f"錯誤: 找不到來源檔案 {file_path}")
        return

    # 讀取來源檔案數據
    with open(file_path, "rb") as input_file:
        input_file_data = input_file.read()

    # 計算並記錄檔案原始大小
    input_file_size = len(input_file_data)

    lz77_data = lz77_compress(input_file_data)
    compressed_data, frequency, padding = huffman_compress(lz77_data)
    output_file_size = len(compressed_data)

    # 開始寫入壓縮檔案
    with open(zip_path, "wb") as output_file:
        # 寫入檔案的二進位壓縮檔數據
        output_file.write(compressed_data)

        print(f"檔案寫入: {file_name} ({input_file_size} bytes) ➔ {zip_name} ({output_file_size} bytes)")

        # 構建並寫入中央目錄
        central_directory.append({
            "filename": file_name,
            "original_size": input_file_size,
            "compressed_size": output_file_size,
            "padding": padding,
            "frequency": frequency
        })

        # 將目錄轉為JSON字串，並編碼為二進位
        directory_json_bytes = json.dumps(central_directory).encode("utf-8")

        # 利用tell()記錄中央目錄，在檔案中的「起始偏移量」
        directory_offset = output_file.tell()

        # 將中央目錄數據寫入檔案尾部
        output_file.write(directory_json_bytes)

        # 在檔案最後寫入4位元組的偏移量，方便日後解讀
        output_file.write(struct.pack("I", directory_offset))

    print("壓縮檔案完成！")

def print_usage():
    print("ZIP功能指令:")
    print("壓縮: python packer.py c <來源檔案路徑>")
    print("解壓縮: python packer.py d <壓縮檔案路徑> <解壓縮資料夾>")

if __name__ == "__main__":
    # 檢查參數數量
    if len(sys.argv) <= 2:
        print("錯誤: 參數不足，請檢查指令格式")
        print_usage()
        sys.exit(1)

    # 讀取指令
    mode = sys.argv[1].lower()

    # 打包壓縮
    if mode == "c":
        if len(sys.argv) == 2:
            print("錯誤: 參數不足，請檢查指令格式")
            print_usage()
            sys.exit(1)
        compress_files(sys.argv[2])

    elif mode == "d":
        if len(sys.argv) == 3:
            print("錯誤: 參數不足，請檢查指令格式")
            print_usage()
            sys.exit(1)
        decompress_files(sys.argv[2], sys.argv[3])

    else:
        print(f"未知指令: {mode}")
        print_usage()
