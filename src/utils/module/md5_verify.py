import re
import hashlib

class MD5Verify:
    def get_md5_from_etag(etag: str) -> str | None:
        if etag:
            if len(etag) == 18 and '"' in etag:
                result = re.findall(r'\w+', etag)

                if result:
                    return result[0]
        
    def verify_md5(md5_value: str, file_path: str):
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        
        return md5_value.lower() == md5.hexdigest()