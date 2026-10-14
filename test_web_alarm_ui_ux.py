"""UX A/B/C HTTP surface and complete human report contract, disposable only."""
from html.parser import HTMLParser
import unittest
import urllib.request

from test_web_alarm_operator_ui import OperatorFixture, tree


class Surface(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs, tuple(self.stack)))
        if tag not in ('input', 'meta', 'link', 'br', 'hr', 'img'):
            self.stack.append(attrs.get('id', tag))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()


class OperatorUxTests(OperatorFixture, unittest.TestCase):
    def test_http_three_regions_single_input_and_no_obsolete_creation_fields(self):
        before = tree(self.root)
        with urllib.request.urlopen(self.url + '/', timeout=5) as response:
            html = response.read().decode('utf-8')
        parsed = Surface()
        parsed.feed(html)
        ids = [attrs['id'] for _, attrs, _ in parsed.nodes if 'id' in attrs]
        self.assertEqual(len(ids), len(set(ids)), 'duplicate DOM IDs')
        regions = [attrs['id'] for tag, attrs, _ in parsed.nodes
                   if tag in ('aside', 'main')]
        self.assertEqual(regions, ['workspacesPanel', 'main', 'tasksPanel'])
        inputs = [(tag, attrs) for tag, attrs, parents in parsed.nodes
                  if 'taskForm' in parents and tag in ('input', 'textarea', 'select')]
        self.assertEqual([(tag, a['id']) for tag, a in inputs], [('textarea', 'taskRaw')])
        self.assertNotIn('required', inputs[0][1])
        self.assertNotIn('navigatorPanel', ids)
        self.assertNotIn('taskTitle', ids)
        self.assertNotIn('taskGoal', ids)
        self.assertEqual(tree(self.root), before)

    def test_large_unicode_reports_stay_bound_to_their_stage_and_get_is_pure(self):
        report = '<img src=x onerror=alert(1)>\n' + 'Проверено: данные и evidence.\n' * 2000
        self.http('/microtasks/m2/report', 'POST',
                  {'task_id': 'task_a', 'report': report, 'operation_id': 'report_ux'})
        before = tree(self.root)
        view = self.ui()
        stages = {m['microtask_id']: m for m in view['operator']['stages']}
        stage_reports = [e['payload']['report'] for e in stages['m2']['events']
                         if e['event_type'] == 'REPORT']
        self.assertEqual(stage_reports, [report.strip()])
        self.assertFalse(any(e['event_type'] == 'REPORT' for e in stages['m1']['events']))
        self.assertEqual(view['reports'][0]['payload']['report'], report.strip())
        self.assertEqual(tree(self.root), before)
        self.facts = [{'report_characters': len(report), 'stage': 'm2',
                       'api_is_read_only': True, 'report_is_plain_text': True}]


if __name__ == '__main__':
    unittest.main()
