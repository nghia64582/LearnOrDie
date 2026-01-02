import java.util.List;
import java.util.ArrayList;


public class Stream {
    public static void main(String[] args) {
        List<Integer> a = new ArrayList<>();
        for (int i = 1; i <= 100; i++) a.add(i);
        
        System.out.println(a.stream().filter(x -> x % 2 == 0).mapToInt(x -> x).sum());
        // Đếm số lẻ
        System.out.println(a.stream().filter(x -> x % 2 == 1).count());


    }
}
