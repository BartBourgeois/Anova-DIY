// Headless post-analysis export for the Anova firmware images. Read-only.
// Args: <outfile> <keyword> [<keyword> ...]
// String->function map built robustly: find literal-pool words that point at a defined string,
// then use Ghidra's reliable ldr->pool references to attribute the string to the function. Also
// direct code->string refs. Then decompile keyword-matching and most string-rich functions.
import java.io.PrintWriter;
import java.util.*;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

public class AnovaExport extends GhidraScript {
    FunctionManager fm;
    Map<Function, List<String>> f2s = new HashMap<>();

    void attribute(Address target, String v) {
        for (Reference r : getReferencesTo(target)) {
            Function f = fm.getFunctionContaining(r.getFromAddress());
            if (f == null) continue;
            f2s.computeIfAbsent(f, x -> new ArrayList<>());
            if (!f2s.get(f).contains(v)) f2s.get(f).add(v);
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "anova_export.txt";
        List<String> kw = new ArrayList<>();
        for (int i = 1; i < args.length; i++) kw.add(args[i].toLowerCase());

        PrintWriter out = new PrintWriter(outPath, "UTF-8");
        fm = currentProgram.getFunctionManager();
        long base = currentProgram.getImageBase().getOffset();

        out.println("# " + currentProgram.getName() + "  lang=" + currentProgram.getLanguageID()
                + "  base=" + currentProgram.getImageBase());
        out.println("keywords: " + kw);
        out.println("\n## memory");
        for (MemoryBlock b : currentProgram.getMemory().getBlocks())
            out.printf("  %-12s %s - %s  %d bytes%n", b.getName(), b.getStart(), b.getEnd(), b.getSize());
        out.println("\n## functions: " + fm.getFunctionCount());

        // 1) collect defined strings: start-address -> value
        Map<Long, String> strAt = new HashMap<>();
        DataIterator it = currentProgram.getListing().getDefinedData(true);
        int strTotal = 0;
        while (it.hasNext()) {
            Data d = it.next();
            Object val = d.getValue();
            if (!(val instanceof String)) continue;
            String v = (String) val;
            if (v.length() < 4) continue;
            strTotal++;
            strAt.put(d.getAddress().getOffset(), v);
        }

        // 2) direct code->string refs
        for (Map.Entry<Long, String> e : strAt.entrySet())
            attribute(currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(e.getKey()),
                    e.getValue());

        // 3) scan memory for pool words that point at a string, then map ldr->pool refs
        int poolPtrs = 0;
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            if (!b.isInitialized()) continue;
            long size = b.getSize();
            byte[] buf = new byte[(int) size];
            b.getBytes(b.getStart(), buf);
            long start = b.getStart().getOffset();
            for (int off = 0; off + 4 <= buf.length; off += 2) {   // step 2: Thumb pools are >=2 aligned
                long w = (buf[off] & 0xffL) | ((buf[off + 1] & 0xffL) << 8)
                        | ((buf[off + 2] & 0xffL) << 16) | ((buf[off + 3] & 0xffL) << 24);
                String v = strAt.get(w);
                if (v == null) continue;
                poolPtrs++;
                attribute(b.getStart().add(off), v);   // ldr -> this pool word
            }
        }
        out.println("## defined strings: " + strTotal + "   pool pointers: " + poolPtrs
                + "   functions with strings: " + f2s.size());

        // keyword hits
        Map<Function, List<String>> kwHits = new LinkedHashMap<>();
        for (Map.Entry<Function, List<String>> e : f2s.entrySet())
            for (String s : e.getValue()) {
                String lv = s.toLowerCase();
                for (String k : kw)
                    if (!k.isEmpty() && lv.contains(k)) {
                        kwHits.computeIfAbsent(e.getKey(), x -> new ArrayList<>());
                        if (!kwHits.get(e.getKey()).contains(s)) kwHits.get(e.getKey()).add(s);
                        break;
                    }
            }

        out.println("\n## keyword string -> function (" + kwHits.size() + ")");
        for (Map.Entry<Function, List<String>> e : kwHits.entrySet()) {
            out.println("  " + e.getKey().getName() + " @ " + e.getKey().getEntryPoint());
            for (String s : e.getValue())
                out.println("      \"" + (s.length() > 100 ? s.substring(0, 100) : s) + "\"");
        }

        List<Function> byCount = new ArrayList<>(f2s.keySet());
        byCount.sort((a, b) -> f2s.get(b).size() - f2s.get(a).size());
        out.println("\n## most string-rich functions (top 60)");
        for (int i = 0; i < byCount.size() && i < 60; i++) {
            Function f = byCount.get(i);
            List<String> ss = f2s.get(f);
            StringBuilder sb = new StringBuilder();
            for (int j = 0; j < ss.size() && j < 6; j++)
                sb.append(" | ").append(ss.get(j).length() > 40 ? ss.get(j).substring(0, 40) : ss.get(j));
            out.println("  " + f.getName() + " @ " + f.getEntryPoint() + " (" + ss.size() + ")" + sb);
        }

        LinkedHashSet<Function> toDecomp = new LinkedHashSet<>(kwHits.keySet());
        for (Function f : byCount) { if (toDecomp.size() >= 45) break; toDecomp.add(f); }
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        out.println("\n## decompiled C (" + toDecomp.size() + " functions)");
        for (Function f : toDecomp) {
            DecompileResults r = dec.decompileFunction(f, 60, monitor);
            out.println("\n/* ===== " + f.getName() + " @ " + f.getEntryPoint()
                    + "  size=" + f.getBody().getNumAddresses()
                    + "  strings=" + (f2s.containsKey(f) ? f2s.get(f).size() : 0) + " ===== */");
            out.println(r != null && r.decompileCompleted()
                    ? r.getDecompiledFunction().getC() : "// decompile failed");
        }
        dec.dispose();
        out.close();
        println("AnovaExport wrote " + outPath + " (funcs=" + fm.getFunctionCount()
                + ", kw=" + kwHits.size() + ", with-strings=" + f2s.size() + ")");
    }
}
