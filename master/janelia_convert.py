from gzip import GzipFile
import logging
import numpy as np
from struct import unpack
from sys import argv


def get_size(format_string):
    return sum(
            size_lookup[_t]
            for _t in list(format_string))


# define constants
size_lookup = {
        "I": 4, # uint32
        "Q": 8, # uint64
        "i": 4, # int32
        "B": 1, # byte
        }
BG_ONLY = 0
FG_ONLY = 1
MIXED = 2
# compute header info for reading
body_header_t = "IIIQ"
body_header_n = get_size(body_header_t)
block_header_t = "iiiB"
block_header_n = get_size(block_header_t)
subblock_header_t = "B"
subblock_header_n = get_size(subblock_header_t)
subblock_t = 64*"B"
subblock_n = get_size(subblock_t)


def assemble_array(mask_list):
    x_list = list()
    y_list = list()
    z_list = list()
    for x, y, z, _ in mask_list:
        x_list.append(x)
        y_list.append(y)
        z_list.append(z)
    x_unique = np.unique(x_list)
    y_unique = np.unique(y_list)
    z_unique = np.unique(z_list)
    min_x = x_unique[0]
    min_y = y_unique[0]
    min_z = z_unique[0]
    max_x = x_unique[-1]
    max_y = y_unique[-1]
    max_z = z_unique[-1]
    dx = x_unique[1] - x_unique[0]
    dy = y_unique[1] - y_unique[0]
    dz = z_unique[1] - z_unique[0]
    block_shape = mask_list[0][-1].shape
    x_space = int(dx/block_shape[0])
    y_space = int(dy/block_shape[1])
    z_space = int(dz/block_shape[2])
    mask_x = max_x - min_x
    mask_x = int(mask_x/x_space) + block_shape[0]
    mask_y = max_y - min_y
    mask_y = int(mask_y/y_space) + block_shape[1]
    mask_z = max_z - min_z
    mask_z = int(mask_z/z_space) + block_shape[2]
    mask_array = np.zeros(
            (
                mask_x,
                mask_y,
                mask_z),
            dtype=np.uint8)
    for x, y, z, block in mask_list:
        x_low = x-min_x
        x_low = int(x_low/x_space)
        x_high = x-min_x
        x_high = int(x_high/x_space)+block_shape[0]
        y_low = y-min_y
        y_low = int(y_low/y_space)
        y_high = y-min_y
        y_high = int(y_high/y_space)+block_shape[1]
        z_low = z-min_z
        z_low = int(z_low/z_space)
        z_high = z-min_z
        z_high = int(z_high/z_space)+block_shape[2]
        mask_array[
                x_low:x_high,
                y_low:y_high,
                z_low:z_high] = block
    return mask_array


def assemble_list(
        body_handle,
        granularity="bit"):
    # read body header
    gx, gy, gz, fg_label = unpack(
            "=" + body_header_t,
            body_handle.read(body_header_n))
    # read body and process blocks
    blocks = list()
    while True:
        _bytes = body_handle.read(block_header_n)
        if len(_bytes) == 0:
            break
        x_block, y_block, z_block, content_flag = unpack(
                "=" + block_header_t,
                _bytes)
        if granularity == "bit":
            block_shape = (8*gx, 8*gy, 8*gz)
        elif granularity == "subblock":
            block_shape = (gx, gy, gz)
        elif granularity == "block":
            block_shape = (1, 1, 1)
        if content_flag == BG_ONLY:
            mask = np.zeros(
                    block_shape,
                    dtype=np.uint8)
        elif content_flag == FG_ONLY:
            mask = np.ones(
                    block_shape,
                    dtype=np.uint8)
        elif content_flag == MIXED:
            mask = assemble_block(
                    gx,
                    gy,
                    gz,
                    body_handle,
                    granularity=granularity)
        else:
            logging.error("invalid content_flag")
        blocks.append((
            x_block,
            y_block,
            z_block,
            mask))
    mask_array = blocks
    return mask_array


def assemble_block(
        gx,
        gy,
        gz,
        body_handle,
        granularity="bit"):
    mask = np.empty(
            (8*gx, 8*gy, 8*gz),
            dtype=np.uint8)
    for s_ix in range(gx*gy*gz):
        x_index = s_ix // (gy*gz)
        y_index = (s_ix // gz) % gy
        z_index = s_ix % gz
        content_flag = unpack(
                "=" + subblock_header_t,
                body_handle.read(subblock_header_n))[0]
        if content_flag == BG_ONLY:
            submask = np.zeros(
                    (8, 8, 8),
                    dtype=np.uint8)
        elif content_flag == FG_ONLY:
            submask = np.ones(
                    (8, 8, 8),
                    dtype=np.uint8)
        elif content_flag == MIXED:
            byte_raw = unpack(
                    "=" + subblock_t,
                    body_handle.read(subblock_n))
            byte_list = list(byte_raw)
            byte_flat = np.array(
                    byte_list,
                    dtype=np.uint8)
            byte_structured = byte_flat.reshape((
                8,
                8,
                1))
            submask = np.flip(
                    np.unpackbits(
                        byte_structured,
                        axis=-1),
                    axis=-1)
        else:
            logging.error("invalid content_flag")
        mask[
                (8*x_index):(8*x_index+8),
                (8*y_index):(8*y_index+8),
                (8*z_index):(8*z_index+8)] = submask
    if granularity == "subblock":
        temp = np.empty(
                (gx, gy, gz),
                dtype=np.uint8)
        for x_index in range(gx):
            for y_index in range(gy):
                for z_index in range(gz):
                    x_low = 8*x_index
                    x_high = x_low+8
                    y_low = 8*y_index
                    y_high = y_low+8
                    z_low = 8*z_index
                    z_high = z_low+8
                    temp[
                            x_index,
                            y_index,
                            z_index] = mask[
                                    x_low:x_high,
                                    y_low:y_high,
                                    z_low:z_high].max()
        mask = temp
    elif granularity == "block":
        mask = np.full(
                (1, 1, 1),
                mask.max(),
                dtype=np.uint8)
    return np.transpose(mask, (2, 1, 0))


if __name__ == "__main__":
    if len(argv) != 3:
        print("usage: python janelia_convert.py <input-name> <output-name>")
    else:
        body_handle = GzipFile(argv[1], "rb")
        mask_list = assemble_list(body_handle, granularity="bit")
        mask_array = assemble_array(mask_list)
        np.save(argv[2], mask_array)
        body_handle.close()
