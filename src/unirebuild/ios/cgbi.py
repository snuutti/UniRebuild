from struct import unpack, pack
from zlib import decompress, compress, crc32


# Copied from https://gist.github.com/urielka/3609051
def cgbi_to_png(cgbi_path: str) -> bytes | None:
    png_header = b"\x89PNG\r\n\x1a\n"

    with open(cgbi_path, "rb") as file:
        cgbi_file = file.read()

    if cgbi_file[:8] != png_header:
        return None

    png_file = cgbi_file[:8]
    chunk_pos = len(png_file)
    idat_acc = b""
    break_loop = False

    # For each chunk in the PNG file
    while chunk_pos < len(cgbi_file):
        skip = False

        # Reading chunk
        chunk_length = cgbi_file[chunk_pos : chunk_pos + 4]
        chunk_length = unpack(">L", chunk_length)[0]
        chunk_type = cgbi_file[chunk_pos + 4 : chunk_pos + 8]
        chunk_data = cgbi_file[chunk_pos + 8 : chunk_pos + 8 + chunk_length]
        chunk_crc = cgbi_file[
            chunk_pos + chunk_length + 8 : chunk_pos + chunk_length + 12
        ]
        chunk_crc = unpack(">L", chunk_crc)[0]
        chunk_pos += chunk_length + 12

        # Parsing the header chunk
        if chunk_type == b"IHDR":
            width = unpack(">L", chunk_data[0:4])[0]
            height = unpack(">L", chunk_data[4:8])[0]

        # Parsing the image chunk
        if chunk_type == b"IDAT":
            idat_acc += chunk_data
            skip = True

        # Remove CgBI chunk
        if chunk_type == b"CgBI":
            skip = True

        # When reaching the end chunk, process the accumulated IDAT data
        if chunk_type == b"IEND":
            try:
                buf_size = width * height * 4 + height
                chunk_data = decompress(idat_acc, -15, buf_size)
            except Exception as e:
                # The PNG image is already normalized
                print(e)
                return None

            # Prepare new IDAT chunk
            chunk_type = b"IDAT"

            # Swap red & blue for each pixel
            new_data = bytearray()
            pos = 0
            for y in range(height):
                # Copy the filter byte for the scanline
                new_data.append(chunk_data[pos])
                pos += 1
                for x in range(width):
                    # Original order: R, G, B, A
                    r = chunk_data[pos]
                    g = chunk_data[pos + 1]
                    b = chunk_data[pos + 2]
                    a = chunk_data[pos + 3]
                    # New order: B, G, R, A
                    new_data.append(b)
                    new_data.append(g)
                    new_data.append(r)
                    new_data.append(a)
                    pos += 4

            # Compress the modified image data
            chunk_data = compress(bytes(new_data))
            chunk_length = len(chunk_data)
            chunk_crc = crc32(chunk_type)
            chunk_crc = crc32(chunk_data, chunk_crc)
            chunk_crc = (chunk_crc + 0x100000000) % 0x100000000
            break_loop = True

        if not skip:
            png_file += pack(">L", chunk_length)
            png_file += chunk_type
            if chunk_length > 0:
                png_file += chunk_data
            png_file += pack(">L", chunk_crc)
        if break_loop:
            break

    png_file += b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"

    return png_file
