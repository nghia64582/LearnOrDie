public class CalcSum implements Runnable {
    private long start;
    private long end;
    private long result;

    public CalcSum(long start, long end) {
        this.start = start;
        this.end = end;
        this.result = 0;
    }

    @Override
    public void run() {
        long startTime = System.currentTimeMillis();
        for (long i = start; i <= end; i++) {
            result += i;
        }
        System.out.println("Sum from " + start + " to " + end + " is " + result + ". Time taken: " + (System.currentTimeMillis() - startTime) + " ms");
    }

    public long getResult() {
        return result;
    }
    
}
