// Headless: apply a curated address->name map, then auto-name the RTOS thread
// functions by resolving the arguments of each call to the task-create wrapper.
// Writes names into the program DB (run WITHOUT -readOnly so they are saved).
// Args: <names.csv>   (columns: address,name,note ; address is hex, no 0x)
import java.io.*;
import java.math.BigInteger;
import java.util.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.lang.Register;
import ghidra.app.cmd.disassemble.ArmDisassembleCommand;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.pcode.*;
import ghidra.program.model.symbol.*;

public class AnovaName extends GhidraScript {

    FunctionManager fm;
    Memory mem;

    String sanitize(String n) {
        StringBuilder b = new StringBuilder();
        for (char c : n.toCharArray())
            if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')
                b.append(c);
            else break;                 // stop at first non-identifier char
        String s = b.toString();
        return s.length() > 60 ? s.substring(0, 60) : s;
    }

    // create a function Ghidra's analysis never defined (a Thumb thread entry reached only
    // through a pointer table): set Thumb mode, disassemble, then create the function.
    Function createThumbFunction(Address a, String name) {
        try {
            try { clearListing(a); } catch (Exception ce) { /* best effort */ }
            ArmDisassembleCommand cmd = new ArmDisassembleCommand(a, null, true); // true = Thumb
            boolean dok = cmd.applyTo(currentProgram, monitor);
            Function f = createFunction(a, name);
            if (f != null) println("  created function " + name + " @ " + a);
            else println("  disasm=" + dok + " but no function @ " + a);
            return f;
        } catch (Exception e) { println("  create failed @ " + a + ": " + e); return null; }
    }

    void rename(Function f, String name) {
        if (f == null || name == null || name.isEmpty()) return;
        try { f.setName(name, SourceType.USER_DEFINED); }
        catch (Exception e) {
            try { f.setName(name + "_" + f.getEntryPoint(), SourceType.USER_DEFINED); } catch (Exception e2) {}
        }
    }

    Long readU32(long addr) {
        try {
            byte[] b = new byte[4];
            mem.getBytes(toAddr(addr), b);
            return (b[0] & 0xffL) | ((b[1] & 0xffL) << 8) | ((b[2] & 0xffL) << 16) | ((b[3] & 0xffL) << 24);
        } catch (Exception e) { return null; }
    }

    // resolve a varnode to a constant pointer value (follows copies, adds, and one load)
    Long resolveConst(Varnode v, int depth) {
        if (v == null || depth > 10) return null;
        if (v.isConstant()) return v.getOffset();
        if (v.isAddress()) return v.getAddress().getOffset();
        PcodeOp d = v.getDef();
        if (d == null) return null;
        switch (d.getOpcode()) {
            case PcodeOp.COPY: case PcodeOp.CAST: case PcodeOp.INT_ZEXT:
            case PcodeOp.INT_SEXT: case PcodeOp.SUBPIECE:
                return resolveConst(d.getInput(0), depth + 1);
            case PcodeOp.INT_ADD: case PcodeOp.PTRSUB: case PcodeOp.PTRADD: {
                Long a = resolveConst(d.getInput(0), depth + 1);
                Long b = resolveConst(d.getInput(1), depth + 1);
                if (a != null && b != null) return a + b;
                return null;
            }
            case PcodeOp.LOAD: {
                Long a = resolveConst(d.getInput(1), depth + 1);   // input1 = address
                return a == null ? null : readU32(a);
            }
            case PcodeOp.INDIRECT:
                return resolveConst(d.getInput(0), depth + 1);
            case PcodeOp.MULTIEQUAL: {
                for (int i = 0; i < d.getNumInputs(); i++) {
                    Long r = resolveConst(d.getInput(i), depth + 1);
                    if (r != null) return r;
                }
                return null;
            }
            default: return null;
        }
    }

    // turn a resolved value into a function: try it directly (Thumb bit0 cleared),
    // then try dereferencing it (the value is the address of a pointer-table slot).
    Function funcFromPtr(Long v) {
        if (v == null) return null;
        Function f = fm.getFunctionAt(toAddr(v & ~1L));
        if (f != null) return f;
        Long v2 = readU32(v);
        if (v2 != null) {
            f = fm.getFunctionAt(toAddr(v2 & ~1L));
            if (f != null) return f;
            f = fm.getFunctionContaining(toAddr(v2 & ~1L));
            if (f != null && f.getEntryPoint().getOffset() == (v2 & ~1L)) return f;
        }
        return null;
    }

    String readCString(long addr) {
        StringBuilder sb = new StringBuilder();
        try {
            for (int i = 0; i < 64; i++) {
                byte x = mem.getByte(toAddr(addr + i));
                if (x == 0) break;
                if (x < 0x20 || x > 0x7e) { if (i == 0) continue; else break; }
                sb.append((char) x);
            }
        } catch (Exception e) {}
        return sb.toString();
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) { println("need <names.csv>"); return; }
        fm = currentProgram.getFunctionManager();
        mem = currentProgram.getMemory();

        // 1) apply the curated CSV
        int applied = 0;
        BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(args[0]), "UTF-8"));
        String line; boolean header = true;
        while ((line = br.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            if (header) { header = false; if (line.toLowerCase().startsWith("address")) continue; }
            int c1 = line.indexOf(',');
            if (c1 < 0) continue;
            String addrHex = line.substring(0, c1).trim();
            String rest = line.substring(c1 + 1);
            String name = rest.indexOf(',') >= 0 ? rest.substring(0, rest.indexOf(',')).trim() : rest.trim();
            name = name.replaceAll("[^A-Za-z0-9_]", "_");
            long off;
            try { off = Long.parseLong(addrHex, 16); } catch (Exception e) { continue; }
            Function f = fm.getFunctionAt(toAddr(off));
            if (f == null) f = fm.getFunctionContaining(toAddr(off));
            if (f == null) f = createThumbFunction(toAddr(off), name);   // not seen by analysis: make it
            if (f != null) { rename(f, name); applied++; }
            else println("  no function at " + addrHex + " (could not create)");
        }
        br.close();
        println("curated names applied: " + applied);

        // 2) find the task-create wrapper (named Task_create by the CSV) and resolve its callers
        Function wrapper = null;
        for (Function f : fm.getFunctions(true))
            if (f.getName().equals("Task_create")) { wrapper = f; break; }
        if (wrapper == null) { println("no Task_create wrapper named; skipping thread resolution"); saveAndReport(applied, 0); return; }

        Address wEntry = wrapper.getEntryPoint();
        Set<Function> callers = new LinkedHashSet<>();
        for (Reference r : getReferencesTo(wEntry)) {
            Function cf = fm.getFunctionContaining(r.getFromAddress());
            if (cf != null) callers.add(cf);
        }
        println("Task_create callers: " + callers.size());

        DecompInterface dec = new DecompInterface();
        dec.setOptions(new DecompileOptions());
        dec.openProgram(currentProgram);
        int threadsNamed = 0;
        for (Function cf : callers) {
            DecompileResults res = dec.decompileFunction(cf, 60, monitor);
            if (res == null || res.getHighFunction() == null) continue;
            Iterator<PcodeOpAST> ops = res.getHighFunction().getPcodeOps();
            while (ops.hasNext()) {
                PcodeOpAST op = ops.next();
                if (op.getOpcode() != PcodeOp.CALL) continue;
                Varnode tgt = op.getInput(0);
                if (tgt == null || !tgt.isAddress() || !tgt.getAddress().equals(wEntry)) continue;
                if (op.getNumInputs() < 3) continue;
                Long nameAddr = resolveConst(op.getInput(1), 0);
                Long fptr     = resolveConst(op.getInput(2), 0);
                if (nameAddr == null || fptr == null) continue;
                String tname = sanitize(readCString(nameAddr));
                if (tname.isEmpty()) continue;
                Function tf = funcFromPtr(fptr);        // handles value-or-pointer-slot, Thumb bit0
                if (tf == null) continue;
                if (tf.getName().startsWith("FUN_")) { rename(tf, tname); threadsNamed++; println("  thread: " + tname + " @ " + tf.getEntryPoint()); }
            }
        }
        dec.dispose();
        saveAndReport(applied, threadsNamed);
    }

    void saveAndReport(int applied, int threads) {
        println("AnovaName done for " + currentProgram.getName()
                + ": curated=" + applied + ", threads resolved=" + threads);
    }
}
