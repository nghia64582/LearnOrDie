class Solution {

    private void dfs(Map<String, PriorityQueue<String>> graph, String from, List<String> result) {
        PriorityQueue<String> tos = graph.get(from);
        while (tos != null && !tos.isEmpty()) {
            String to = tos.poll();
            dfs(graph, to, result);
        }
        result.add(0, from);
    }

    public List<String> findItinerary(List<List<String>> tickets) {
        Map<String, PriorityQueue<String>> graph = new HashMap<>();
        for (List<String> ticket : tickets) {
            String from = ticket.get(0);
            String to = ticket.get(1);
            if (!graph.containsKey(from)) {
                graph.put(from, new PriorityQueue<>());
            }
            graph.get(from).add(to);
        }
        List<String> result = new ArrayList<>();
        dfs(graph, "JFK", result);
        return result;
    }
}