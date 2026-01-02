
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ThreadPoolTest {
    public static void main(String[] args) {
        // create 2 thread pool with 1 and 8 threads to calculate sum from 1 to 1000000
        ExecutorService pool1 = Executors.newFixedThreadPool(1);
        ExecutorService pool8 = Executors.newFixedThreadPool(2);
        long n = 10000000;
        long start1 = System.currentTimeMillis();
        pool1.submit(new CalcSum(1, n));
        pool1.shutdown();
        long end1 = System.currentTimeMillis();
        long start8 = System.currentTimeMillis();
        long range = n / 2;
        for (int i = 0; i < 2; i++) {
            long start = i * range + 1;
            long end = (i == 1) ? n : (i + 1) * range;
            pool8.submit(new CalcSum(start, end));
        }
        long end8 = System.currentTimeMillis();

    }
    
}
