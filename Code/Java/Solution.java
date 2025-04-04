class Solution {
    public int minOperations(String s) {
        int count = 0;
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) == '1' && i % 2 == 0) {
                count++;
            } else if (s.charAt(i) == '0' && i % 2 == 1) {
                count++;
            }
        }
        return Math.min(count, s.length() - count);
    }
}