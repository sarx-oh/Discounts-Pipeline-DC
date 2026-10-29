"""Check export provenance and rejection of unexpected private workspace paths."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from export_databricks_release import export


class WorkspaceExportTests(unittest.TestCase):
    def test_exports_remote_bytes_and_uses_native_source_format(self):
        remote = '/Users/test/project'
        contents = {'README.md':b'# Remote source\n', 'notebooks/run.py':b'# Databricks notebook source\nx = 1\n'}
        formats = {}
        def cli(command, **kwargs):
            if command[1:3] == ['workspace', 'list']:
                objects = ([{'path':remote+'/README.md','object_type':'FILE'},
                            {'path':remote+'/notebooks','object_type':'DIRECTORY'}]
                           if command[3] == remote else
                           [{'path':remote+'/notebooks/run.py','object_type':'NOTEBOOK'}])
                return subprocess.CompletedProcess(command, 0, json.dumps(objects), '')
            name = command[3].removeprefix(remote+'/')
            formats[name] = command[command.index('--format')+1]
            Path(command[command.index('--file')+1]).write_bytes(contents[name])
            return subprocess.CompletedProcess(command, 0, '', '')
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.run', side_effect=cli), patch('export_databricks_release.validate', return_value=[]):
            target = Path(directory)/'fresh'
            result = export(remote, target, 'test')
            self.assertEqual((target/'README.md').read_bytes(), contents['README.md'])
            self.assertEqual(formats, {'README.md':'AUTO','notebooks/run.py':'SOURCE'})
            self.assertEqual(len(result['files']), 2)
            with self.assertRaisesRegex(ValueError, 'must not exist'):
                export(remote, target, 'test')

    def test_rejects_private_tree_before_creating_destination(self):
        remote = '/Users/test/project'
        listing = json.dumps([{'path':remote+'/output','object_type':'DIRECTORY'}])
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.run', return_value=subprocess.CompletedProcess([],0,listing,'')):
            target = Path(directory)/'fresh'
            with self.assertRaisesRegex(ValueError, 'Private runtime path'):
                export(remote, target, 'test')
            self.assertFalse(target.exists())

    def test_rejects_object_outside_requested_root(self):
        listing = json.dumps([{'path':'/Users/other/secret.py','object_type':'FILE'}])
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.run', return_value=subprocess.CompletedProcess([],0,listing,'')):
            target = Path(directory)/'fresh'
            with self.assertRaises(ValueError):
                export('/Users/test/project', target, 'test')
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
