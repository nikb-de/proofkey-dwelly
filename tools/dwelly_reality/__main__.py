import argparse
import json
from .runner import prepare, run, export


def main():
    parser=argparse.ArgumentParser(description='Frozen submitted model on official decision-time inputs; zero operational effects.')
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare'); p.add_argument('--source',required=True); p.add_argument('--output',required=True)
    p.add_argument('--sidecars'); p.add_argument('--expected-cases',type=int,default=30)
    p.add_argument('--system-file'); p.add_argument('--effort',choices=('low','medium','high'))
    r=commands.add_parser('run'); r.add_argument('--prepared',required=True); r.add_argument('--profile',action='append',required=True)
    r.add_argument('--live',action='store_true'); r.add_argument('--provider-env-file')
    r.add_argument('--concurrency',type=int,default=3); r.add_argument('--cap-usd',type=float,default=25)
    r.add_argument('--deadline-seconds',type=float,default=900)
    e=commands.add_parser('export'); e.add_argument('--prepared',required=True); e.add_argument('--output',required=True); e.add_argument('--profile',required=True)
    args=parser.parse_args()
    if args.command=='prepare': result=prepare(args.source,args.output,sidecars=args.sidecars,expected_cases=args.expected_cases,
        system_file=args.system_file,effort=args.effort)
    elif args.command=='run': result=run(args.prepared,args.profile,live=args.live,provider_env_file=args.provider_env_file,
        concurrency=args.concurrency,cap_usd=args.cap_usd,deadline_seconds=args.deadline_seconds)
    else: result=export(args.prepared,args.output,args.profile)
    print(json.dumps({key:value for key,value in result.items() if key not in ('source_files','code_files','cases')},ensure_ascii=False))

if __name__=='__main__': main()
