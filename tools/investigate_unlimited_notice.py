"""Read-only evidence for the screenshot's untranslated Unlimited Mode notice."""
import hashlib
import json
import re
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pc_idx import Archive, GAME, used_ids

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/unlimited_notice_location'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    exe=(GAME/'WO3U.exe').read_bytes()
    phrase='11因\x1bC5龙穴\x1bR的效果，获得了开眼之书！'
    raw=phrase.encode('gbk')
    offsets=[m.start() for m in re.finditer(re.escape(raw+b'\0'),exe)]
    assert offsets, 'expected exact EXE string absent'
    pe=struct.unpack_from('<I',exe,0x3c)[0]
    nsec=struct.unpack_from('<H',exe,pe+6)[0]
    optsize=struct.unpack_from('<H',exe,pe+20)[0]
    image_base=struct.unpack_from('<Q',exe,pe+24+24)[0]
    sections=[]
    for i in range(nsec):
        p=pe+24+optsize+40*i
        name=exe[p:p+8].rstrip(b'\0').decode('ascii','replace')
        vs,va,rs,rp=struct.unpack_from('<IIII',exe,p+8)
        for off in offsets:
            if rp<=off<rp+rs:
                sections.append({'name':name,'file_offset':hex(off),'rva':hex(va+off-rp),
                                 'preferred_va':hex(image_base+va+off-rp)})
    cs=json.loads((ROOT/'mapping/ko_charset.json').read_text('utf8'))['chars']
    reverse={bytes.fromhex(h):ch for ch,h in cs.items()}
    display=re.sub(rb'\x1b(?:C[0-9]|R)',b'',raw[2:])
    decoded=[];tokens=[];i=0
    while i<len(display):
        b=display[i:i+1] if display[i]<128 else display[i:i+2]
        decoded.append(reverse.get(b,b.decode('gbk')));tokens.append(b);i+=len(b)
    a=Archive('CHS',GAME)
    atlas_data=a.read(38)
    atlas=Image.frombytes('RGBA',(4096,8192),atlas_data[56:],'bcn',3).getchannel('A')
    codes=struct.unpack_from('<9888H',exe,0xB936EE)[1:-1]
    cell={c:k for k,c in enumerate(codes)}
    im=Image.new('RGB',(max(1000,48*len(tokens)+32),200),(20,24,32))
    dr=ImageDraw.Draw(im);font=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf',22)
    dr.text((12,8),'현재 설치 폰트 + EXE 원본 바이트로 재구성 (게임 캡처 아님)',font=font,fill='white')
    for col,b in enumerate(tokens):
        c=int.from_bytes(b,'big');k=cell.get(c)
        if k is not None:
            x=k%85*48;y=k//85*48
            im.paste((255,255,255),(12+col*48,56,60+col*48,104),atlas.crop((x,y,x+48,y+48)))
        else:dr.text((12+col*48,56),b.decode('ascii','replace'),font=font,fill='white')
    dr.text((12,125),'원뜻: 용혈의 효과로 개안의 서를 획득했습니다!',font=font,fill='white')
    im.save(OUT/'exe_notice_actual_glyphs.png')
    print('EXE',sections,'glyphs',''.join(decoded),flush=True)
    needle='的效果，获得了开眼之书！'.encode('gbk')
    archive_hits=[];scanned=0;errors=[]
    for e in used_ids(a.idx):
        try:d=a.read(e)
        except Exception as err:errors.append([e,str(err)]);continue
        scanned+=1
        for label,b in [('full',raw),('body_without_leading_control',raw[2:]),('suffix',needle)]:
            off=d.find(b)
            if off>=0:archive_hits.append({'entry':e,'kind':label,'offset':hex(off)})
    catalog_hits=[]
    for line in (ROOT/'extract/pc_catalog.jsonl').open(encoding='utf8'):
        r=json.loads(line)
        if '开眼之书' in (r.get('CHS') or '') and '龙穴' in (r.get('CHS') or ''):
            catalog_hits.append(r)
    idx_hash=hashlib.sha256((GAME/'LINKIDX_CHS.BIN').read_bytes()).hexdigest().upper()
    known=[]
    for p in (ROOT/'build').glob('*/build_report.json'):
        r=json.loads(p.read_text('utf8'))
        if r['files']['LINKIDX_CHS.BIN']['sha256'].upper()==idx_hash:known.append(p.parent.name)
    inv=json.loads((ROOT/'inventory/pc_inventory.json').read_text('utf8'))
    orig_exe=next(r['sha256'] for r in inv['files'] if r['path']=='WO3U.exe')
    exe_hash=hashlib.sha256(exe).hexdigest().upper()
    result={'exact_exe_match':sections,'source_chs':phrase,'raw_hex':raw.hex(),
            'korean_glyph_interpretation':''.join(decoded),'meaning_ko':'용혈의 효과로 개안의 서를 획득했습니다!',
            'installed_exe_sha256':exe_hash,'exe_matches_original_inventory':exe_hash==orig_exe.upper(),
            'installed_idx_sha256':idx_hash,'matching_build_idx':known,
            'chs_payloads_scanned':scanned,'chs_exact_byte_hits':archive_hits,'archive_read_errors':errors,
            'original_multilanguage_catalog_matches':catalog_hits,
            'scope':'Installed CHS payloads and original extracted text catalog; no exhaustive search of base parts 000-003.',
            'runtime_memory_traced':False,'game_files_modified':False}
    (OUT/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
