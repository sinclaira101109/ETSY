import base64
import csv
import io
import json
import os
import socket
import subprocess
import time
import unittest
import pandas as pd
import urllib.error
import urllib.request

from app import analyze, render_report, ingest_upload, reference_only_report


def sample(**values):
    record = {'title': 'Three-Towel Rose Bouquet with Lace Wrapping', 'tags': 'towel bouquet,rose gift,towel bouquet'}
    record.update(values)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=record.keys())
    writer.writeheader()
    writer.writerow(record)
    return stream.getvalue().encode('utf-8-sig')


class ReportTests(unittest.TestCase):
    def test_unknown_data_never_becomes_zero_conversion_or_missing_online_fields(self):
        result = analyze(sample())
        listing = result['listings'][0]
        self.assertIsNone(listing['conversion_rate'])
        description = next(f for f in listing['findings'] if f['code'] == 'description_unknown')
        self.assertEqual(description['status'], '资料未提供')
        rendered = render_report(result)
        self.assertIn('暂无可比数据', rendered)
        self.assertNotIn('0.0%', rendered)
        self.assertNotIn('平均 SEO 分数', rendered)
        json.dumps(result, allow_nan=False)

    def test_non_csv_formats_are_ingested_without_being_metrics(self):
        from zipfile import ZipFile
        pdf_payload, pdf_docs = ingest_upload('notes.txt', '产品买点和包装说明'.encode('utf-8'))
        self.assertEqual(pdf_payload, [])
        self.assertIn('产品买点', pdf_docs[0]['text'])
        xlsx = io.BytesIO()
        with pd.ExcelWriter(xlsx, engine='openpyxl') as writer:
            pd.DataFrame({'title': ['A towel bouquet'], 'tags': ['towel gift']}).to_excel(writer, index=False)
        payloads, docs = ingest_upload('products.xlsx', xlsx.getvalue())
        self.assertEqual(len(payloads), 1)
        self.assertEqual(docs, [])
        archive = io.BytesIO()
        with ZipFile(archive, 'w') as z:
            z.writestr('products.csv', 'title,tags\nA towel bouquet,towel gift\n')
            z.writestr('../unsafe.csv', 'title,tags\nBad,bad\n')
        payloads, docs = ingest_upload('bundle.zip', archive.getvalue())
        self.assertEqual(len(payloads), 1)
        self.assertTrue(any('不安全路径' in note for doc in docs for note in doc['notes']))

    def test_zero_orders_with_declared_period_differs_from_unknown(self):
        listing = analyze(sample(visits='100', orders='0', period_start='2026-10-01', period_end='2026-10-07'))['listings'][0]
        self.assertEqual(listing['conversion_rate'], 0)
        self.assertTrue(any(f['code'] == 'performance_review' for f in listing['findings']))

    def test_views_units_section_materials_are_not_equivalent_metrics(self):
        result = analyze(sample(views='100', quantity_sold='3', section='Gifts', materials='cotton'))
        self.assertIsNone(result['listings'][0]['conversion_rate'])
        self.assertIsNone(result['field_map']['分类'])
        self.assertIsNone(result['field_map']['属性'])
        self.assertIsNone(result['field_map']['订单数'])

    def test_invalid_counts_and_period_are_not_comparable(self):
        for values in [dict(visits='-1', orders='1'), dict(visits='10', orders='2', period_start='2026-10-07', period_end='2026-10-01'), dict(visits='10', orders='100'), dict(visits='10', orders='1.5')]:
            self.assertIsNone(analyze(sample(**values))['listings'][0]['conversion_rate'])

    def test_evidence_explanations_and_actions_are_present(self):
        result = analyze(sample(description='', category='Gifts', image_count='3'))
        for f in result['listings'][0]['findings']:
            for key in ('evidence', 'interpretation', 'reason', 'actions', 'verification', 'confidence', 'alternatives'):
                self.assertTrue(f[key])
        self.assertTrue(any(f['code'] == 'tag_format' for f in result['listings'][0]['findings']))
        self.assertTrue(any(f['code'] == 'description_clarity' and f['status'] == '已观察' for f in result['listings'][0]['findings']))

    def test_html_escapes_uploaded_content(self):
        rendered = render_report(analyze(sample(title='<script>alert(1)</script>')))
        self.assertNotIn('<script>alert(1)</script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_aggregate_counts_no_row_truncation(self):
        data = b'title,tags\n' + b'Towel bouquet,towel gift\n' * 55
        result = analyze(data)
        self.assertEqual(len(result['listings']), 55)
        self.assertEqual(next(f['count'] for f in result['bottlenecks'] if f['code'] == 'description_unknown'), 55)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{port}'
        cls.proc = subprocess.Popen(['.venv/bin/uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(port)],
            env={**os.environ, 'APP_USER': 'test', 'APP_PASSWORD': 'test-only-password'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(cls.url)
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    break
            except OSError:
                time.sleep(.1)
        else:
            cls.proc.terminate()
            raise RuntimeError('Server failed readiness')
        cls.auth = 'Basic ' + base64.b64encode(b'test:test-only-password').decode()

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)

    def upload(self, data):
        body = b'--test-boundary\r\nContent-Disposition: form-data; name="files"; filename="shop.csv"\r\nContent-Type: text/csv\r\n\r\n' + data + b'\r\n--test-boundary--\r\n'
        request = urllib.request.Request(self.url + '/analyze', body, headers={'Authorization': self.auth, 'Content-Type': 'multipart/form-data; boundary=test-boundary'})
        return urllib.request.urlopen(request)

    def test_real_upload_returns_detailed_html(self):
        with self.upload(sample()) as response:
            body = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn('text/html', response.headers['Content-Type'])
            self.assertIn('观察证据', body)
            self.assertIn('执行动作', body)
            self.assertIn('逐 TAG 核对记录', body)
            self.assertIn('0.5.0', body)

    def test_multiple_files_and_shop_context_are_reported(self):
        data_a = sample(title="A towel bouquet", tags="towel gift,rose gift")
        data_b = sample(title="A second towel gift", tags="towel gift,housewarming")
        body = b''
        for name, data in ((b"products.csv", data_a), (b"traffic.csv", data_b)):
            body += b"--test-boundary\r\nContent-Disposition: form-data; name=\"files\"; filename=\"" + name + b"\"\r\nContent-Type: text/csv\r\n\r\n" + data + b"\r\n"
        body += b"--test-boundary\r\nContent-Disposition: form-data; name=\"shop_url\"\r\n\r\nhttps://www.etsy.com/shop/HoryalfTowelFlowers\r\n--test-boundary--\r\n"
        request = urllib.request.Request(self.url + '/analyze', body, headers={'Authorization': self.auth, 'Content-Type': 'multipart/form-data; boundary=test-boundary'})
        with urllib.request.urlopen(request) as response:
            rendered = response.read().decode()
        self.assertIn('products.csv', rendered)
        self.assertIn('traffic.csv', rendered)
        self.assertIn('HoryalfTowelFlowers', rendered)
        self.assertIn('逐 TAG 核对记录', rendered)

    def test_auxiliary_csv_is_retained_with_reason(self):
        with self.upload(b'keyword,search_volume\ntowel gift,100\n') as response:
            body = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn('未合并的辅助文件', body)
            self.assertIn('title 或 listing_id', body)


if __name__ == '__main__':
    unittest.main()


