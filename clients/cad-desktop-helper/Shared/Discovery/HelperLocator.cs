using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Yuantus.Cad.Shared.Transport;

namespace Yuantus.Cad.Shared.Discovery
{
    public sealed class HelperLocator
    {
        public static readonly TimeSpan DefaultMaxWait = TimeSpan.FromSeconds(5);
        public static readonly TimeSpan DefaultPollInterval = TimeSpan.FromMilliseconds(100);

        private readonly HelperProbe _probe;
        private readonly Func<HelperSessionFile> _readSessionFile;
        private readonly Func<Process> _spawn;
        private readonly TimeSpan _maxWait;
        private readonly TimeSpan _pollInterval;

        public HelperLocator()
            : this(new HelperProbe(), HelperSessionFile.Read, HelperSpawner.Spawn, DefaultMaxWait, DefaultPollInterval)
        {
        }

        public HelperLocator(
            HelperProbe probe,
            Func<HelperSessionFile> readSessionFile,
            Func<Process> spawn,
            TimeSpan maxWait,
            TimeSpan pollInterval)
        {
            _probe = probe;
            _readSessionFile = readSessionFile;
            _spawn = spawn;
            _maxWait = maxWait;
            _pollInterval = pollInterval;
        }

        public async Task<Uri> EnsureHelperRunningAsync(CancellationToken cancellationToken)
        {
            var existing = _readSessionFile();
            if (existing != null)
            {
                var probe = await _probe.HealthAsync(existing.Port, cancellationToken).ConfigureAwait(false);
                if (probe.IsHealthy)
                {
                    return existing.ToBaseUri();
                }
            }

            _spawn();
            var started = DateTimeOffset.UtcNow;
            while (DateTimeOffset.UtcNow - started < _maxWait)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var current = _readSessionFile();
                if (current != null)
                {
                    var probe = await _probe.HealthAsync(current.Port, cancellationToken).ConfigureAwait(false);
                    if (probe.IsHealthy)
                    {
                        return current.ToBaseUri();
                    }
                }
                await Task.Delay(_pollInterval, cancellationToken).ConfigureAwait(false);
            }

            throw new HelperException(
                ErrorCodes.HelperPortBusy,
                "Timed out waiting for yuantus-cad-helper.exe /healthz.",
                true);
        }
    }
}
