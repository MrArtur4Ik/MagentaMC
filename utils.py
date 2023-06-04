import gzip, io

def remove_spaces(b: bytes):
	while True:
		if b.endswith(b' '):
			b = b[0:-1]
		else:
			break
	return b.decode("utf8", errors="ignore")

def add_spaces(s: str):
	b = s.encode("utf8", errors="ignore")
	while True:
		if len(b) > 64:
			b = b[0:64]
		elif len(b) < 64:
			b = b + (b' ' * (64-len(b)))
		else:
			break
	return b

def segment_byte_array(b: bytes): #Делит массив байтов на сегменты по 1024 байта
	return [b[i:i + 1024] for i in range(0, len(b), 1024)]

def segment_string(s: str):
	return [s[i:i + 64] for i in range(0, len(s), 64)]

def compress(data, compresslevel=9):
    """Compress data in one shot and return the compressed string.
    Optional argument is the compression level, in range of 1-9.
    """

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=compresslevel) as f:
        f.write(data)

    return buf.getvalue()

def decompress(data):
    """Decompress a gzip compressed string in one shot.
    Return the decompressed string.
    """

    with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
        data = f.read()

    return data