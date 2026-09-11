"""Native-source preview is AST-only. Execution belongs exclusively to a trusted worker."""
import ast
import importlib.metadata
import importlib.util
import re
import sys

from terminal.data import canonical,digest,write_new


def validate_native(document):
    fields={"version","engine","engine_version","source","class_name","config_class","config","bar_minutes","dependencies","provenance"}
    if not isinstance(document,dict) or set(document)!=fields or document["version"]!=1:
        raise ValueError("Invalid native strategy document")
    if document["engine"]!="nautilus_trader" or document["engine_version"]!="1.231.0":
        raise ValueError("Supported native format: NautilusTrader 1.231.0")
    source=document["source"]
    if not isinstance(source,str) or len(source.encode())>512*1024: raise ValueError("Native source exceeds 512 KiB")
    if not isinstance(document["config"],dict) or not isinstance(document["dependencies"],dict): raise ValueError("Native config/dependencies must be objects")
    for name in ("class_name","config_class"):
        if not isinstance(document[name],str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,100}",document[name]):
            raise ValueError("Expected a class name defined or imported by this module")
    periods=document["bar_minutes"]
    if not isinstance(periods,list) or not 1<=len(periods)<=6 or len(set(periods))!=len(periods) or any(type(p) is not int or p not in (1,3,5,15,30,60,120,240,360,720,1440) for p in periods):
        raise ValueError("Declare up to six supported native bar timeframes")
    if not isinstance(document["provenance"],str) or not document["provenance"].strip() or len(document["provenance"])>2000:
        raise ValueError("Record source/dependency provenance and license information")
    for name,version in document["dependencies"].items():
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",name) or not isinstance(version,str) or not re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}",version):
            raise ValueError("Dependencies must name installed distributions and exact versions")
    tree=ast.parse(source)
    if sum(1 for _ in ast.walk(tree))>30000: raise ValueError("Native preview exceeds AST resource budget")
    return tree


def trust_identity(document):
    return digest({key:document[key] for key in ("source","engine","engine_version","dependencies")})


def preview(document):
    tree=validate_native(document)
    classes=[node.name for node in tree.body if isinstance(node,ast.ClassDef)]
    imports=sorted({node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) and node.module} |
                   {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names})
    problems=[]
    for package,expected in document["dependencies"].items():
        try: actual=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: actual=None
        if actual!=expected: problems.append({"package":package,"expected":expected,"installed":actual})
    return {"trust_sha256":trust_identity(document),"classes":classes,"imports":imports,"dependency_problems":problems,
            "warning":"Python executes with your user permissions. The worker controls lifetime, not security. Preview does not prove safety or complete compatibility."}


def load_trusted(document,directory,instrument_id):
    """Call only after worker verifies recorded consent for this exact source hash."""
    report=preview(document)
    if report["dependency_problems"]:
        raise ValueError("Native dependencies are missing or incompatible; review and install them separately")
    from nautilus_trader.config import StrategyConfig
    from nautilus_trader.trading.strategy import Strategy
    file=directory/"native_strategy.py"
    write_new(file,document["source"].encode())
    name="terminal_native_"+report["trust_sha256"]
    spec=importlib.util.spec_from_file_location(name,file)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    try:
        spec.loader.exec_module(module)
        strategy_class=getattr(module,document["class_name"])
        config_class=getattr(module,document["config_class"])
        if not isinstance(strategy_class,type) or not issubclass(strategy_class,Strategy) or not isinstance(config_class,type) or not issubclass(config_class,StrategyConfig):
            raise ValueError("Expected native Strategy and StrategyConfig subclasses")
        def expand(value):
            if value=="$instrument": return str(instrument_id)
            if isinstance(value,str) and re.fullmatch(r"\$bar:[0-9]+",value):
                minutes=int(value.split(":")[1])
                if minutes not in document["bar_minutes"]: raise ValueError("Config references an undeclared native timeframe")
                return f"{instrument_id}-{minutes}-MINUTE-LAST-EXTERNAL"
            if isinstance(value,dict): return {k:expand(v) for k,v in value.items()}
            if isinstance(value,list): return [expand(v) for v in value]
            return value
        return strategy_class(config_class.parse(canonical(expand(document["config"]))))
    except ModuleNotFoundError as exc:
        raise ValueError(f"Missing Python dependency '{exc.name}'; nothing was installed automatically") from exc


class NativeDataGateway:
    """Reject unavailable native data features instead of a silent empty feed."""
    def __init__(self,engine,instrument_id,bar_types):
        self.engine=engine
        self.instrument_id=instrument_id
        self.bar_types=set(bar_types)
        self.violations=[]
        self.original_execute=engine.kernel.data_engine.execute
        self.original_request=engine.kernel.data_engine.request
        bus=engine.kernel.msgbus
        bus.deregister("DataEngine.execute",self.original_execute)
        bus.register("DataEngine.execute",self.execute)
        bus.deregister("DataEngine.request",self.original_request)
        bus.register("DataEngine.request",self.request)

    def execute(self,command):
        from nautilus_trader.data.messages import SubscribeBars,UnsubscribeBars,SubscribeInstrument
        allowed=False
        if isinstance(command,(SubscribeBars,UnsubscribeBars)):
            allowed=str(command.bar_type) in self.bar_types
        elif isinstance(command,SubscribeInstrument):
            allowed=command.instrument_id==self.instrument_id
        if not allowed:
            self.violations.append(f"Unsupported native data subscription: {type(command).__name__}")
            return
        self.original_execute(command)

    def request(self,command):
        self.violations.append(f"Native historical requests are unsupported: {type(command).__name__}; preload declared external bars instead")

    def assert_supported(self):
        if self.violations: raise ValueError("; ".join(dict.fromkeys(self.violations)))
