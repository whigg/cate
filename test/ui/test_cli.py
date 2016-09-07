import os
import sys
import unittest
from time import sleep

from ect.core.monitor import Monitor
from ect.core.util import fetch_std_streams
from ect.ui import cli


class CliTest(unittest.TestCase):
    def test_noargs(self):
        sys.argv = []
        with fetch_std_streams():
            status = cli.main()
            self.assertEqual(status, 0)

    def test_invalid_command(self):
        with fetch_std_streams():
            status = cli.main(['pipo'])
            self.assertEqual(status, 2)

    def test_option_version(self):
        with fetch_std_streams():
            status = cli.main(args=['--version'])
            self.assertEqual(status, 0)

    def test_option_help(self):
        with fetch_std_streams():
            status = cli.main(args=['--h'])
            self.assertEqual(status, 0)
            status = cli.main(args=['--help'])
            self.assertEqual(status, 0)

    def test_parse_load_arg(self):
        self.assertEqual(cli._parse_load_arg('sst2011=SST_LT_ATSR_L3U_V01.0_ATSR1'),
                         ('sst2011', 'SST_LT_ATSR_L3U_V01.0_ATSR1', None, None))
        self.assertEqual(cli._parse_load_arg('sst2011=SST_LT_ATSR_L3U_V01.0_ATSR1,2011'),
                         ('sst2011', 'SST_LT_ATSR_L3U_V01.0_ATSR1', '2011', None))
        self.assertEqual(cli._parse_load_arg('SST_LT_ATSR_L3U_V01.0_ATSR1,,2012'),
                         (None, 'SST_LT_ATSR_L3U_V01.0_ATSR1', None, '2012'))
        self.assertEqual(cli._parse_load_arg('=SST_LT_ATSR_L3U_V01.0_ATSR1'),
                         (None, 'SST_LT_ATSR_L3U_V01.0_ATSR1', None, None))
        self.assertEqual(cli._parse_load_arg('sst2011='),
                         ('sst2011', None, None, None))

    def test_parse_write_arg(self):
        self.assertEqual(cli._parse_write_arg('/home/norman/data'), (None, '/home/norman/data', None))
        self.assertEqual(cli._parse_write_arg('/home/norman/.git'), (None, '/home/norman/.git', None))
        self.assertEqual(cli._parse_write_arg('/home/norman/im.png'), (None, '/home/norman/im.png', None))
        self.assertEqual(cli._parse_write_arg('/home/norman/im.png,PNG'), (None, '/home/norman/im.png', 'PNG'))
        self.assertEqual(cli._parse_write_arg('ds=/home/norman/data.nc,netcdf4'),
                         ('ds', '/home/norman/data.nc', 'NETCDF4'))


class CliOperationCommandTest(unittest.TestCase):
    def test_command_op_info(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'info', 'ect.ops.timeseries.timeseries'])
            self.assertEqual(status, 0)
        self.assertIn('Extract time-series', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'info', 'foobarbaz'])
            self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), "ect: error: command 'op info': unknown operation 'foobarbaz'\n")

        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'info'])
            self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn("usage: ect op info [-h] OP\n", stderr.getvalue())

    def test_command_op_list(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'list'])
            self.assertEqual(status, 0)
        self.assertIn('operations found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'list', '-n', '*data*'])
            self.assertEqual(status, 0)
        self.assertIn('operations found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'list', '-n', 'nevermatch'])
            self.assertEqual(status, 0)
        self.assertIn('No operations found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['op', 'list', '--tag', 'io'])
            self.assertEqual(status, 0)
        self.assertIn('9 operations found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')


class CliDataSourceCommandTest(unittest.TestCase):
    def test_command_ds_info(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['ds', 'info', 'SOIL_MOISTURE_DAILY_FILES_ACTIVE_V02.2'])
            self.assertEqual(status, 0)
        self.assertIn('Base directory', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

    def test_command_ds_list(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['ds', 'list'])
            self.assertEqual(status, 0)
        self.assertIn('98 data sources found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['ds', 'list', '--id', 'CLOUD*'])
            self.assertEqual(status, 0)
        self.assertIn('19 data sources found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

    @unittest.skip(reason="skipped unless you want to debug data source synchronisation")
    def test_command_ds_sync(self):
        with fetch_std_streams():
            status = cli.main(args=['ds', 'sync', 'SOIL_MOISTURE_DAILY_FILES_ACTIVE_V02.2'])
            self.assertEqual(status, 0)

    @unittest.skip(reason="skipped unless you want to debug data source synchronisation")
    def test_command_ds_sync_with_period(self):
        with fetch_std_streams():
            status = cli.main(args=['ds', 'sync', 'SOIL_MOISTURE_DAILY_FILES_ACTIVE_V02.2', '--time', '2010-12'])
            self.assertEqual(status, 0)

    def test_command_ds_parse_time_period(self):
        from ect.ui.cli import DataSourceCommand
        from datetime import date

        self.assertEqual(DataSourceCommand.parse_time_period('2010'), (date(2010, 1, 1), date(2010, 12, 31)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-02'), (date(2010, 2, 1), date(2010, 2, 28)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-12'), (date(2010, 12, 1), date(2010, 12, 31)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-02-04'), (date(2010, 2, 4), date(2010, 2, 4)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-12-31'), (date(2010, 12, 31), date(2010, 12, 31)))

        self.assertEqual(DataSourceCommand.parse_time_period('2010,2014'), (date(2010, 1, 1), date(2014, 12, 31)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-02,2010-09'), (date(2010, 2, 1), date(2010, 9, 30)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-12,2011-12'),
                         (date(2010, 12, 1), date(2011, 12, 31)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-02-04,2019-02-04'),
                         (date(2010, 2, 4), date(2019, 2, 4)))
        self.assertEqual(DataSourceCommand.parse_time_period('2010-12-31,2010-01-06'),
                         (date(2010, 12, 31), date(2010, 1, 6)))

        # errors
        self.assertEqual(DataSourceCommand.parse_time_period('2010-12-31,2010-01'), None)
        self.assertEqual(DataSourceCommand.parse_time_period('2010,2010-01'), None)
        self.assertEqual(DataSourceCommand.parse_time_period('2010-01,2010-76'), None)
        self.assertEqual(DataSourceCommand.parse_time_period('2010-1-3-83,2010-01'), None)
        self.assertEqual(DataSourceCommand.parse_time_period('20L0-1-3-83,2010-01'), None)

    def test_command_run_no_args(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['ds'])
            self.assertEqual(status, 0)
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(stdout.getvalue(),
                         "usage: ect ds [-h] COMMAND ...\n"
                         "\n"
                         "Manage data sources.\n"
                         "\n"
                         "positional arguments:\n"
                         "  COMMAND     One of the following commands. Type \"COMMAND -h\" to get command-\n"
                         "              specific help.\n"
                         "    list      List all available data sources\n"
                         "    sync      Synchronise a remote data source with its local version.\n"
                         "    info      Display information about a data source.\n"
                         "\n"
                         "optional arguments:\n"
                         "  -h, --help  show this help message and exit\n")


class CliRunCommandTest(unittest.TestCase):
    def test_command_run_with_unknown_op(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['run', 'pipapo', 'lat=13.2', 'lon=52.9'])
            self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), "ect: error: command 'run': unknown operation 'pipapo'\n")

    def test_command_run_noargs(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['run'])
            self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), "ect: error: command 'run' requires OP argument\n")

    def test_command_run_with_op(self):
        from ect.core.op import OP_REGISTRY as OP_REGISTRY

        op_reg = OP_REGISTRY.add_op(timeseries, fail_if_exists=True)

        try:
            # Run without --monitor and --write
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(args=['run', op_reg.op_meta_info.qualified_name, 'lat=13.2', 'lon=52.9'])
                self.assertEqual(status, 0)
            self.assertIn("Running '", stdout.getvalue())
            self.assertIn('lat=13.2 lon=52.9 method=nearest', stdout.getvalue())
            self.assertIn('Output: [0.3, 0.25, 0.05, 0.4, 0.2, 0.1, 0.5]', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), '')

            # Run with --monitor and without --write
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(args=['run', '--monitor', op_reg.op_meta_info.qualified_name, 'lat=13.2', 'lon=52.9'])
                self.assertEqual(status, 0)
            self.assertIn("Running '", stdout.getvalue())
            self.assertIn('lat=13.2 lon=52.9 method=nearest', stdout.getvalue())
            self.assertIn('Extracting timeseries data: started', stdout.getvalue())
            self.assertIn('Extracting timeseries data:  33%', stdout.getvalue())
            self.assertIn('Extracting timeseries data: done', stdout.getvalue())
            self.assertIn('Output: [0.3, 0.25, 0.05, 0.4, 0.2, 0.1, 0.5]', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), '')

            # Run with --monitor and --write
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(
                    args=['run', '--monitor', '--write', 'timeseries_data.txt', op_reg.op_meta_info.qualified_name,
                          'lat=13.2',
                          'lon=52.9'])
                self.assertEqual(status, 0)
            self.assertIn("Running '", stdout.getvalue())
            self.assertIn('lat=13.2 lon=52.9 method=nearest', stdout.getvalue())
            self.assertIn('Extracting timeseries data: started', stdout.getvalue())
            self.assertIn('Extracting timeseries data:  33%', stdout.getvalue())
            self.assertIn('Extracting timeseries data: done', stdout.getvalue())
            self.assertIn('Writing output to timeseries_data.txt using TEXT format...', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), '')
            self.assertTrue(os.path.isfile('timeseries_data.txt'))
            os.remove('timeseries_data.txt')

            # Run with invalid keyword
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(args=['run', op_reg.op_meta_info.qualified_name, 'l*t=13.2', 'lon=52.9'])
                self.assertEqual(status, 2)
            self.assertEqual(stdout.getvalue(), '')
            self.assertEqual(stderr.getvalue(), "ect: error: command 'run': keyword 'l*t' is not a valid identifier\n")

        finally:
            OP_REGISTRY.remove_op(op_reg.operation, fail_if_not_exists=True)

    def test_command_run_with_workflow(self):
        from ect.core.op import OP_REGISTRY as OP_REGISTRY
        import os.path

        op_reg = OP_REGISTRY.add_op(timeseries, fail_if_exists=True)

        workflow_file = os.path.join(os.path.dirname(__file__), 'timeseries.json')
        self.assertTrue(os.path.exists(workflow_file), msg='missing test file %s' % workflow_file)

        try:
            # Run without --monitor and --write
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(args=['run', workflow_file, 'lat=13.2', 'lon=52.9'])
                self.assertEqual(status, 0)
            self.assertIn("Running '", stdout.getvalue())
            self.assertIn('lat=13.2 lon=52.9', stdout.getvalue())
            self.assertIn('Output: [0.3, 0.25, 0.05, 0.4, 0.2, 0.1, 0.5]', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), '')

            # Run with --monitor and without --write
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(args=['run', '--monitor', workflow_file, 'lat=13.2', 'lon=52.9'])
                self.assertEqual(status, 0)
            self.assertIn("Running '", stdout.getvalue())
            self.assertIn('lat=13.2 lon=52.9', stdout.getvalue())
            self.assertIn('Extracting timeseries data: started', stdout.getvalue())
            self.assertIn('Extracting timeseries data:  33%', stdout.getvalue())
            self.assertIn('Extracting timeseries data: done', stdout.getvalue())
            self.assertIn('Output: [0.3, 0.25, 0.05, 0.4, 0.2, 0.1, 0.5]', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), '')

            # Run with --monitor and --write
            with fetch_std_streams() as (stdout, stderr):
                status = cli.main(
                    args=['run', '--monitor', '--write', 'timeseries_data.json', workflow_file, 'lat=13.2', 'lon=52.9'])
                self.assertEqual(status, 0)
            self.assertIn("Running '", stdout.getvalue())
            self.assertIn('lat=13.2 lon=52.9', stdout.getvalue())
            self.assertIn('Extracting timeseries data: started', stdout.getvalue())
            self.assertIn('Extracting timeseries data:  33%', stdout.getvalue())
            self.assertIn('Extracting timeseries data: done', stdout.getvalue())
            self.assertIn('Writing output to timeseries_data.json using JSON format...', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), '')
            self.assertTrue(os.path.isfile('timeseries_data.json'))
            os.remove('timeseries_data.json')

        finally:
            OP_REGISTRY.remove_op(op_reg.operation, fail_if_not_exists=True)

    def test_command_run_help(self):
        with fetch_std_streams():
            status = cli.main(args=['run', '-h'])
            self.assertEqual(status, 0)

        with fetch_std_streams():
            status = cli.main(args=['run', '--help'])
            self.assertEqual(status, 0)


class CliPluginCommandTest(unittest.TestCase):
    def test_command_list(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['pi', 'list'])
            self.assertEqual(status, 0)
        self.assertIn('plugins found', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')


class CliLicenseCommandTest(unittest.TestCase):
    def test_command_license(self):
        with fetch_std_streams() as (stdout, stderr):
            status = cli.main(args=['lic'])
            self.assertEqual(status, 0)
        self.assertIn('GNU General Public License', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')


def timeseries(lat: float, lon: float, method: str = 'nearest', monitor=Monitor.NULL) -> list:
    """Timeseries dummy function for testing."""
    print('lat=%s lon=%s method=%s' % (lat, lon, method))
    work_units = [0.3, 0.25, 0.05, 0.4, 0.2, 0.1, 0.5]
    with monitor.starting('Extracting timeseries data', sum(work_units)):
        for work_unit in work_units:
            sleep(work_unit / 10.)
            monitor.progress(work_unit)
    return work_units


def timeseries2(var, lat: float, lon: float, method: str = 'nearest', monitor=Monitor.NULL) -> list:
    """Timeseries dummy function for testing."""
    print('lat=%s lon=%s method=%s' % (lat, lon, method))
    work_units = [0.3, 0.25, 0.05, 0.4, 0.2, 0.1, 0.5]
    with monitor.starting('Extracting timeseries data', sum(work_units)):
        for work_unit in work_units:
            sleep(work_unit / 10.)
            monitor.progress(work_unit)
    ts = var[0, 0]
    return ts
