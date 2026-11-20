# scripts/run_eval_night.ps1
# One night of the home evaluation of the RL study (docs/rl_plan.md). Plays the queue below with scripts/rl_round.py evaluate,
# in priority order (the held-out plan families first: they carry H6), and stops at the deadline. Every run folder resumes when
# the command is played again, so the next night continues where this one stopped. The private seed is read by rl_round.py from
# .env and is never printed here. Condition B, k = 3, Ollama, Docker sandbox, as in the plan.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_eval_night.ps1 [-StopAt 07:00] [-DryRun]
param(
    [string]$StopAt = "07:00",      # local time: the night ends here, even in the middle of an episode (it resumes next time)
    [switch]$DryRun                 # print the queue and what is missing, play nothing
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$RlDir = if ($env:RL_DIR) { $env:RL_DIR } else { Join-Path $Root "runs\rl" }
New-Item -ItemType Directory -Force $RlDir | Out-Null
$Log = Join-Path $RlDir ("night-" + (Get-Date -Format "yyyyMMdd") + ".log")
function Say($m) { $l = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $m; Add-Content -Path $Log -Value $l -Encoding utf8; Write-Host $l }

# Priority order. arm = folder name (eval-<arm>-<part>), tag = Ollama tag made by scripts/rl_gguf.py.
$Models = @(
    @{ arm = "base";       tag = "qwen3-4b" },
    @{ arm = "t0-reward";  tag = "t0-reward" },
    @{ arm = "t1-reward";  tag = "t1-reward" },
    @{ arm = "t2-reward";  tag = "t2-reward" },
    @{ arm = "t0-format";  tag = "t0-format" },
    @{ arm = "t1-format";  tag = "t1-format" },
    @{ arm = "t2-format";  tag = "t2-format" }
)
$Reward = $Models | Where-Object { $_.arm -eq "base" -or $_.arm -like "*-reward" }
$Format = $Models | Where-Object { $_.arm -like "*-format" }
$Queue = @()
foreach ($m in $Reward) { $Queue += @{ arm = $m.arm; tag = $m.tag; part = "held" } }     # step 1: H6 (arm 0 and arm 2)
foreach ($m in $Format) { $Queue += @{ arm = $m.arm; tag = $m.tag; part = "held" } }     # step 2: the control arm
foreach ($m in $Models) { $Queue += @{ arm = $m.arm; tag = $m.tag; part = "rest" } }     # step 3: the other 98 instances

$Deadline = [datetime]::ParseExact($StopAt, "HH:mm", $null)
if ($Deadline -le (Get-Date)) { $Deadline = $Deadline.AddDays(1) }
Say "night starts, stops at $Deadline, log $Log"

function Have-Docker { docker info *> $null; return ($LASTEXITCODE -eq 0) }
function Have-Ollama { ollama list *> $null; return ($LASTEXITCODE -eq 0) }

if (-not $DryRun) {
    if (-not (Have-Docker)) {
        Say "starting Docker Desktop"
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        for ($i = 0; $i -lt 36 -and -not (Have-Docker); $i++) { Start-Sleep 5 }
    }
    if (-not (Have-Ollama)) {
        Say "starting ollama serve"
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 12 -and -not (Have-Ollama); $i++) { Start-Sleep 5 }
    }
    if (-not (Have-Docker)) { Say "Docker does not answer: stop"; exit 2 }
    if (-not (Have-Ollama)) { Say "Ollama does not answer: stop"; exit 2 }
}

$Tags = (ollama list 2>$null | Select-Object -Skip 1 | ForEach-Object { ($_ -split "\s+")[0] -replace ":latest$", "" })
foreach ($job in $Queue) {
    $name = "$($job.arm) / $($job.part)"
    if ($Tags -notcontains $job.tag) { Say "SKIP $name : no Ollama tag '$($job.tag)' (not converted yet)"; continue }
    if ($DryRun) { Say "would play $name"; continue }
    $left = ($Deadline - (Get-Date)).TotalSeconds
    if ($left -le 120) { Say "deadline reached before $name"; break }
    Say "START $name ($([int]($left/60)) min left)"
    # Play it in its own process so that it can be stopped at the deadline. Output goes next to the run folder.
    $out = Join-Path $RlDir ("night-" + $job.arm + "-" + $job.part + ".out")
    $p = Start-Process -FilePath $Python -PassThru -NoNewWindow `
        -ArgumentList @("scripts\rl_round.py", "evaluate", "--arm", $job.arm, "--tag", $job.tag, "--part", $job.part) `
        -RedirectStandardOutput $out -RedirectStandardError ($out + ".err")
    if (-not $p.WaitForExit([int]($left * 1000))) {
        Say "deadline: stopping $name (it resumes next night)"
        taskkill /PID $p.Id /T /F *> $null
        # sandbox containers of an interrupted episode: remove them so that the next night starts clean
        $c = docker ps -aq --filter "name=orbitbench" 2>$null
        if ($c) { docker rm -f $c *> $null }
        break
    }
    Say "END $name exit code $($p.ExitCode)"
    if ($p.ExitCode -ne 0) { Say "WARNING $name did not finish cleanly: see $out.err (it will be resumed next night)" }
}
Say "night over"
