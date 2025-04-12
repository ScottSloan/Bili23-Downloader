import re
import hashlib

class MD5Verify:
    def get_md5_from_etag(etag: str):
        if "-" in etag:
            return None
        
        elif '"' in etag:
            return re.findall(r'\w+', etag)[0]
        
    def verify_md5(md5_value: str, file_path: str):
        if not md5_value:
            return False
        
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        
        return md5_value.lower() == md5.hexdigest()