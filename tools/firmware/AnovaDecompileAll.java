// Headless post-analysis: decompile EVERY function into a browsable source tree. Read-only.
// Args: <outDir>
// Writes under <outDir>:
//   functions/<name>.c   one decompiled C function per file (named, so you can open by function)
//   all.c                every function concatenated in address order (one grep target)
//   prototypes.h         one line per function: its recovered signature + address
//   index.csv            address,end,size_bytes,name,file,params,calls_out,called_by
//   strings.txt          every defined string with its address (navigation aid)
//   <prog>.c / <prog>.h  whole-program C export WITH type definitions (Ghidra CppExporter; best effort)
import java.io.*;
import java.util.*;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.app.util.Option;
import ghidra.app.util.exporter.CppExporter;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataUtilities;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryBlock;

public class AnovaDecompileAll extends GhidraScript {

    static String sanitize(String n) {
        StringBuilder b = new StringBuilder();
        for (char c : n.toCharArray())
            b.append((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
                    || c == '_' || c == '.' || c == '-' ? c : '_');
        String s = b.toString();
        if (s.length() > 120) s = s.substring(0, 120);
        return s;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) { println("need <outDir>"); return; }
        File outDir = new File(args[0]);
        File fnDir = new File(outDir, "functions");
        fnDir.mkdirs();

        FunctionManager fm = currentProgram.getFunctionManager();
        int total = fm.getFunctionCount();
        println("decompiling " + total + " functions of " + currentProgram.getName());

        // functions in address order
        List<Function> funcs = new ArrayList<>();
        for (Function f : fm.getFunctions(true)) funcs.add(f);
        funcs.sort(Comparator.comparing(f -> f.getEntryPoint()));

        DecompInterface dec = new DecompInterface();
        DecompileOptions opts = new DecompileOptions();
        dec.setOptions(opts);
        dec.openProgram(currentProgram);

        PrintWriter all  = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(new File(outDir, "all.c")), "UTF-8"));
        PrintWriter proto = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(new File(outDir, "prototypes.h")), "UTF-8"));
        PrintWriter idx  = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(new File(outDir, "index.csv")), "UTF-8"));

        all.println("/* " + currentProgram.getName() + " - all decompiled functions, address order.");
        all.println("   language=" + currentProgram.getLanguageID() + " base=" + currentProgram.getImageBase());
        all.println("   Recovered by decompilation; names like FUN_xxxx are auto-generated. */\n");
        proto.println("/* " + currentProgram.getName() + " - recovered function prototypes */");
        idx.println("address,end,size_bytes,name,file,params,calls_out,called_by");

        Set<String> used = new HashSet<>();
        int ok = 0, fail = 0, i = 0;
        for (Function f : funcs) {
            i++;
            if (i % 100 == 0) println("  " + i + "/" + total);
            String base = sanitize(f.getName());
            String fname = base + ".c";
            if (!used.add(fname.toLowerCase())) {
                fname = base + "__" + f.getEntryPoint() + ".c";
                used.add(fname.toLowerCase());
            }
            long size = f.getBody().getNumAddresses();
            int params = f.getParameterCount();
            int callsOut, calledBy;
            try { callsOut = f.getCalledFunctions(monitor).size(); } catch (Exception e) { callsOut = -1; }
            try { calledBy = f.getCallingFunctions(monitor).size(); } catch (Exception e) { calledBy = -1; }

            String proto1;
            try { proto1 = f.getPrototypeString(false, false); } catch (Exception e) { proto1 = f.getSignature().getPrototypeString(); }
            proto.println(proto1 + "   /* @" + f.getEntryPoint() + " */");

            idx.println(f.getEntryPoint() + "," + f.getBody().getMaxAddress() + "," + size + ","
                    + f.getName() + "," + fname + "," + params + "," + callsOut + "," + calledBy);

            DecompileResults r = dec.decompileFunction(f, 90, monitor);
            String c = (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null)
                    ? r.getDecompiledFunction().getC() : null;
            if (c == null) { c = "/* decompile failed: " + (r != null ? r.getErrorMessage() : "null") + " */\n"
                    + "/* " + proto1 + " @ " + f.getEntryPoint() + " */\n"; fail++; } else ok++;

            String banner = "/* ===== " + f.getName() + " @ " + f.getEntryPoint()
                    + "  size=" + size + " bytes  params=" + params
                    + "  calls_out=" + callsOut + "  called_by=" + calledBy + " ===== */\n";

            PrintWriter pf = new PrintWriter(new OutputStreamWriter(
                    new FileOutputStream(new File(fnDir, fname)), "UTF-8"));
            pf.print(banner);
            pf.print(c);
            pf.close();

            all.print("\n" + banner);
            all.print(c);
        }
        dec.dispose();
        all.close(); proto.close(); idx.close();
        println("per-function: ok=" + ok + " fail=" + fail);

        // defined strings -> strings.txt (navigation aid)
        PrintWriter st = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(new File(outDir, "strings.txt")), "UTF-8"));
        int ns = 0;
        DataIterator di = currentProgram.getListing().getDefinedData(true);
        while (di.hasNext()) {
            Data d = di.next();
            Object v = d.getValue();
            if (!(v instanceof String)) continue;
            String s = ((String) v).replace("\n", "\\n").replace("\r", "\\r");
            if (s.length() < 3) continue;
            st.println(d.getAddress() + "\t" + s);
            ns++;
        }
        st.close();
        println("strings: " + ns);

        // whole-program C with type definitions (best effort; never fatal)
        try {
            File cfile = new File(outDir, currentProgram.getName() + ".c");
            CppExporter exp = new CppExporter();
            List<Option> eopts = exp.getOptions(() -> currentProgram);
            if (eopts != null) {
                for (Option o : eopts) {
                    String nm = o.getName().toLowerCase();
                    if ((nm.contains("header") || nm.contains("type") || nm.contains("function"))
                            && (o.getValue() instanceof Boolean))
                        o.setValue(Boolean.TRUE);
                }
                exp.setOptions(eopts);
            }
            boolean cok = exp.export(cfile, currentProgram, null, monitor);
            println("CppExporter whole-program export: " + cok + " -> " + cfile.getName());
        } catch (Throwable t) {
            println("CppExporter skipped: " + t);
        }

        println("AnovaDecompileAll done for " + currentProgram.getName() + " -> " + outDir);
    }
}
