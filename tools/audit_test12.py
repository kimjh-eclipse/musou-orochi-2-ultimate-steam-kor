"""Read-only subtitle/font audit, independent byte decoding and installed-file checks.

Writes evidence only under reports/test12_audit; never launches or changes the game.
"""
import collections
import hashlib
import json
import struct
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from pc_idx import Archive, GAME, used_ids
from kt_text import walk
from ko_charset import table_codes, is_hanzi_code
from build_font import fonts, render

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/test12_audit'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest().upper()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cs = json.loads((ROOT/'mapping/ko_charset.json').read_text('utf8'))['chars']
    old = json.loads((ROOT/'mapping/ko_charset.v1_sorted.json').read_text('utf8'))['chars']
    reverse = {bytes.fromhex(h): ch for ch, h in cs.items()}
    assert len(reverse) == len(cs), 'duplicate donor code'
    codes = table_codes()
    assert len(codes) == len(set(codes)), 'duplicate engine table code'
    cell = {c: k for k, c in enumerate(codes)}
    def decode(raw):
        out, pos = [], 0
        while pos < len(raw):
            if raw[pos] < 128:
                out.append(chr(raw[pos])); pos += 1
            else:
                b = raw[pos:pos+2]
                assert len(b) == 2
                out.append(reverse[b] if b in reverse else ('\ue032' if b == b'\xaa\xa1' else b.decode('gbk')))
                pos += 2
        return ''.join(out)
    matches = collections.defaultdict(dict)
    for line in (ROOT/'mapping/pc_match.jsonl').open(encoding='utf8'):
        r=json.loads(line); matches[r['entry']][tuple(r['path'])]=r
    overrides={}
    for p in sorted((ROOT/'translation_memory').glob('pc_ko_*.jsonl')):
        for line in p.open(encoding='utf8'):
            if line.strip():
                r=json.loads(line); overrides[r['jp']]=r['ko']
    new=Archive('CHS', ROOT/'build/test12'); orig=Archive('CHS'); jp=Archive('JPN')
    stats=collections.Counter(); errors=[]; used=set(); entry_counts={}; samples=[]
    for e, rows in sorted(matches.items()):
        src={s.path:s for s in walk(jp.read(e), '<')}
        built={s.path:s for s in walk(new.read(e), '<')}
        if src.keys()!=built.keys(): errors.append(['path_set',e])
        ec=collections.Counter()
        for path,s in built.items():
            r=rows.get(path); source=src[path].raw.decode('cp932','replace')
            expected=overrides.get(source)
            if expected is None and r and r['level'] in {'exact_path','entry_text','global_text','conflict','global_fill'}:
                expected=r['ko']
            actual=decode(s.raw)
            if expected is not None:
                stats['translated_checked']+=1
                if actual!=expected: errors.append(['text',e,path,expected,actual])
            for ch in actual:
                if '\uac00'<=ch<='\ud7a3': used.add(ch)
            pos=0
            while pos<len(s.raw):
                if s.raw[pos]<128: pos+=1; continue
                b=s.raw[pos:pos+2]; ec['double_byte']+=1
                if len(b)!=2 or not all(0xa1<=v<=0xfe for v in b):
                    ec['non_euc']+=1
                    errors.append(['non_euc',e,path,pos,b.hex()])
                pos+=2
            if (e,path) in {(33,(5,9970)),(33,(4,949))}:
                samples.append({'entry':e,'path':path,'ko':actual,'raw':s.raw.hex()})
        entry_counts[str(e)]=dict(ec)
        stats.update(ec)
    print('text audit',dict(stats),'errors',len(errors),flush=True)
    font=new.read(38)
    atlas=Image.frombytes('RGBA',(4096,8192),font[56:],'bcn',3).getchannel('A')
    a=np.asarray(atlas).astype(np.int16); fl=fonts(); glyphs=[]
    for ch in sorted(used):
        k=cell[int(cs[ch],16)]; x=(k%85)*48; y=(k//85)*48
        target,_=render(ch,fl)
        actual=a[y:y+48,x:x+48]
        # Independent Pillow decoder vs pre-compression raster; DXT alpha permits bounded error.
        delta=np.abs(actual-target.astype(np.int16))
        g={'ch':ch,'code':cs[ch],'cell':k,'max_error':int(delta.max()),'mean_error':float(delta.mean())}
        glyphs.append(g)
        if delta.max()>19 or not actual.max(): errors.append(['font',g])
    print('font audit',len(glyphs),'errors',len(errors),flush=True)
    # Every engine-table cell outside donor allocation is untouched, including padding beyond table.
    baseline=orig.read(38); donor_blocks=set()
    for h in cs.values():
        k=cell[int(h,16)]; x=(k%85)*12; y=(k//85)*12
        donor_blocks.update((y+dy)*1024+x+dx for dy in range(12) for dx in range(12))
    blocks=np.frombuffer(font[56:],dtype=np.uint8).reshape(-1,16)
    ob=np.frombuffer(baseline[56:],dtype=np.uint8).reshape(-1,16)
    changed=np.flatnonzero(np.any(blocks!=ob,axis=1))
    outside=[int(i) for i in changed if int(i) not in donor_blocks]
    if outside or font[:56]!=baseline[:56]: errors.append(['outside_donor',outside[:20]])
    files={}
    for name in ('LINKIDX_CHS.BIN','LINKFILE_CHS.BIN'):
        built_hash=sha(ROOT/'build/test12'/name); installed_hash=sha(GAME/name)
        files[name]={'build':built_hash,'installed':installed_hash,'identical':built_hash==installed_hash}
        if built_hash!=installed_hash: errors.append(['installed',name])
    old_unsafe=[ch for ch in sorted(used) if not all(0xa1<=b<=0xfe for b in bytes.fromhex(old[ch]))]
    new_unsafe=[ch for ch in sorted(used) if not all(0xa1<=b<=0xfe for b in bytes.fromhex(cs[ch]))]
    # Actual atlas preview, not a font-only mockup.
    lines=['전생하면 레벨이 1이 됩니다.','성장 구슬을 획득할 수 있습니다.','언리미티드 모드의 자막을 확인합니다.']
    sheet=Image.new('RGB',(1200,len(lines)*100),(20,24,32))
    ref=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf',24)
    dr=ImageDraw.Draw(sheet)
    for row,line in enumerate(lines):
        dr.text((8,row*100+4),'원문: '+line,font=ref,fill='white')
        for col,ch in enumerate(line):
            if ch in cs:
                k=cell[int(cs[ch],16)]; x=k%85*48; y=k//85*48
                mask=atlas.crop((x,y,x+48,y+48))
                sheet.paste((255,255,255),(col*36,row*100+42,col*36+36,row*100+78),mask.resize((36,36)))
            else:
                dr.text((col*36,row*100+42),ch,font=ref,fill='white')
    sheet.save(OUT/'actual_font_preview.png')
    report={'time':time.strftime('%Y-%m-%d %H:%M:%S'),'build':'test12','scope':'static; no runtime confirmation',
            'stats':dict(stats),'used_hangul':len(used),'old_unsafe_count':len(old_unsafe),
            'old_unsafe_examples':old_unsafe[:40],'new_unsafe_count':len(new_unsafe),
            'glyphs_checked':len(glyphs),'font_max_error':max(g['max_error'] for g in glyphs),
            'outside_donor_changed_blocks':len(outside),'files':files,'samples':samples,
            'entry_counts':entry_counts,'errors':errors,'passed':not errors}
    (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'samples','entry_counts'}},ensure_ascii=False,indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__=='__main__': main()
