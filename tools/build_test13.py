"""Verified incremental build: test12 + Korean boot notice, all other entries identical.

Checks source hashes against the independent test12 audit, rebuilds the notice from
the pristine CHS source, and compares every resulting archive entry. No installation.
"""
import copy
import json
import time
from pathlib import Path

from pc_idx import Archive, used_ids
from pack_lang import write_part, sha256
from g1t_pc import parse, decode, replace
from boot_notice import render_notice, swap_rb

ROOT=Path(__file__).resolve().parents[1]


def main():
    base=ROOT/'build/test12'; out=ROOT/'build/test13'
    assert not out.exists(), 'test13 already exists; keep build artifacts immutable'
    audit=json.loads((ROOT/'reports/test12_audit/audit.json').read_text('utf8'))
    assert audit['passed']
    for name,r in audit['files'].items():
        assert sha256(base/name)==r['build'], 'baseline changed'
    mapping=ROOT/'mapping/ko_charset.json'
    spec_path=ROOT/'mapping/images/14753.json'
    spec=json.loads(spec_path.read_text('utf8'))['textures'][0]['boot_notice']
    original=Archive('CHS').read(14753); t=parse(original)['tex'][0]
    im,notice_report=render_notice(decode(original,t),spec)
    replacement=replace(original,t,im)
    assert len(replacement)==len(original)
    assert replacement[:t['data']]==original[:t['data']]
    assert decode(replacement,t).tobytes()==im.tobytes(), 'notice roundtrip mismatch'
    write_part('CHS',{14753:replacement},out,source_dir=base)
    before=Archive('CHS',base); after=Archive('CHS',out)
    assert used_ids(before.idx)==used_ids(after.idx)
    changed=[]
    for e in used_ids(before.idx):
        assert len(after.read(e))==after.idx[e][1], e
        if before.raw(e)!=after.raw(e): changed.append(e)
    assert changed==[14753], changed
    assert after.read(14753)==replacement
    rep=copy.deepcopy(json.loads((base/'build_report.json').read_text('utf8')))
    rep.update(version='test13',built=time.strftime('%Y-%m-%d %H:%M:%S'),
               baseline='test12',changed_from_baseline=changed,
               baseline_files=audit['files'],charset_sha256=sha256(mapping),
               notice_spec_sha256=sha256(spec_path),runtime_verified=False)
    assert not any(r['entry']==14753 for r in rep['images'])
    rep['images'].append({'entry':14753,'tex':0,'labels':notice_report})
    rep['entries_replaced']+=1
    rep['files']={n:{'size':(out/n).stat().st_size,'sha256':sha256(out/n)}
                  for n in ('LINKIDX_CHS.BIN','LINKFILE_CHS.BIN')}
    (out/'build_report.json').write_text(json.dumps(rep,ensure_ascii=False,indent=1),'utf8')
    (out/'untranslated_queue.jsonl').write_bytes((base/'untranslated_queue.jsonl').read_bytes())
    (out/'ko_charset.json').write_bytes(mapping.read_bytes())
    reports=ROOT/'reports/test13';reports.mkdir(parents=True,exist_ok=True)
    swap_rb(decode(after.read(14753),t)).crop(spec['visible_rect']).save(reports/'boot_notice_ko.png')
    result={'passed':True,'baseline':'test12','changed_entries':changed,
            'unchanged_entries':len(used_ids(before.idx))-1,'all_entries_decompressed':True,
            'notice_lossless_readback':True,'font_and_text_identical_to_audited_test12':True,
            'runtime_verified':False,'files':rep['files']}
    (reports/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
