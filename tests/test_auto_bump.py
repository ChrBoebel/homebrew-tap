import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile
import shutil
import subprocess
import os
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('auto_bump', Path(__file__).parents[1] / 'scripts/auto-bump.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PREFIX = 'https://www.christopherboebel.com/downloads/saywing'

class ReleasePlanTests(unittest.TestCase):
    def setUp(self):
        self.arm = dict(version='0.1.32', build='132', architecture='arm64', sha256='a'*64,
                        url=PREFIX+'/Saywing-0.1.32-132.dmg')
        self.intel = dict(self.arm, architecture='x86_64', sha256='b'*64,
                          url=PREFIX+'/x86_64/Saywing-0.1.32-132.dmg')
        self.cask = '  version "0.1.31,131"\n  on_arm do\n    sha256 "'+'c'*64+'"\n  end\n  on_intel do\n    sha256 "'+'d'*64+'"\n  end\n'
        self.release = dict(tag_name='v0.1.32-build132', draft=False, published_at='2026-11-05T00:00:00Z', prerelease=True)

    def test_published_beta_updates_both_architectures(self):
        self.assertEqual(mod.plan(self.arm,self.intel,self.cask,self.release), ('0.1.32','132'))

    def test_partial_publication_waits(self):
        self.intel['build']='131'
        self.assertIsNone(mod.plan(self.arm,self.intel,self.cask,self.release))

    def test_no_release_or_draft_waits(self):
        self.assertIsNone(mod.plan(self.arm,self.intel,self.cask,None))
        self.release['draft']=True
        self.assertIsNone(mod.plan(self.arm,self.intel,self.cask,self.release))

    def test_wrong_tag_rejected(self):
        self.release['tag_name']='v0.1.33-build133'
        with self.assertRaises(ValueError): mod.plan(self.arm,self.intel,self.cask,self.release)

    def test_bad_metadata_rejected(self):
        for key,value in [('version','1.2;evil'),('build','0'),('sha256','z'*64),('architecture','x86_64'),('url','https://evil.test/package.dmg')]:
            with self.subTest(key=key):
                arm=copy.deepcopy(self.arm);arm[key]=value
                with self.assertRaises(ValueError): mod.plan(arm,self.intel,self.cask,self.release)

    def test_same_release_is_noop_but_changed_hash_rejected(self):
        updated=self.cask.replace('0.1.31,131','0.1.32,132').replace('c'*64,'a'*64).replace('d'*64,'b'*64)
        self.assertIsNone(mod.plan(self.arm,self.intel,updated,self.release))
        self.arm['sha256']='e'*64
        with self.assertRaises(ValueError): mod.plan(self.arm,self.intel,updated,self.release)

    def test_no_downgrade(self):
        self.assertIsNone(mod.plan(self.arm,self.intel,self.cask.replace('0.1.31,131','0.1.33,133'),self.release))

class ExecutionTests(unittest.TestCase):
    def setUp(self):
        ReleasePlanTests.setUp(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'Casks').mkdir()
        (self.root/'Casks/saywing.rb').write_text(self.cask)

    def test_dry_run_never_mutates(self):
        with patch.object(mod,'ROOT',self.root), patch.object(mod,'feed',side_effect=[self.arm,self.intel]), patch.object(mod,'api',return_value=self.release), patch.object(mod,'command') as cmd:
            mod.run(True)
            cmd.assert_not_called()
        self.assertEqual((self.root/'Casks/saywing.rb').read_text(),self.cask)

    def test_existing_pr_recovers_audit_without_new_commit(self):
        pr={'state':'open','head':{'sha':'abc'},'html_url':'https://github.com/ChrBoebel/homebrew-tap/pull/1'}
        with patch.object(mod,'ROOT',self.root), patch.object(mod,'feed',side_effect=[self.arm,self.intel]), patch.object(mod,'api',side_effect=[self.release,[pr]]), patch.object(mod,'audit') as audit, patch.object(mod,'command') as cmd:
            mod.run()
            audit.assert_called_once_with('codex/bump-saywing-0.1.32-132','abc')
            cmd.assert_not_called()

    def test_closed_pr_is_not_reopened(self):
        with patch.object(mod,'ROOT',self.root), patch.object(mod,'feed',side_effect=[self.arm,self.intel]), patch.object(mod,'api',side_effect=[self.release,[{'state':'closed','html_url':'closed'}]]), patch.object(mod,'audit') as audit:
            mod.run()
            audit.assert_not_called()

    def test_existing_audit_is_not_dispatched_again(self):
        with patch.object(mod,'command',return_value='[{"databaseId": 123}]') as cmd:
            mod.audit('branch','abc')
            self.assertEqual(cmd.call_count,1)

    def test_bump_script_with_real_offline_feeds(self):
        (self.root/'scripts').mkdir()
        shutil.copy(Path(__file__).parents[1]/'scripts/bump.sh',self.root/'scripts/bump.sh')
        feeds=self.root/'feeds';(feeds/'x86_64').mkdir(parents=True)
        import json
        (feeds/'latest.json').write_text(json.dumps(self.arm))
        (feeds/'x86_64/latest.json').write_text(json.dumps(self.intel))
        env=dict(os.environ,SAYWING_DOWNLOAD_PREFIX=feeds.as_uri())
        subprocess.run(['bash',str(self.root/'scripts/bump.sh')],env=env,check=True,capture_output=True)
        updated=(self.root/'Casks/saywing.rb').read_text()
        self.assertIn('0.1.32,132',updated)
        self.assertIn('a'*64,updated)
        self.assertIn('b'*64,updated)
        self.intel['build']='133'
        (feeds/'x86_64/latest.json').write_text(json.dumps(self.intel))
        result=subprocess.run(['bash',str(self.root/'scripts/bump.sh')],env=env,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.root/'Casks/saywing.rb').read_text(),updated)

if __name__ == '__main__': unittest.main()
