import os
import re
import networkx as nx
import matplotlib.pyplot as plt

def find_java_files(root_dir):
    java_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
    return java_files

def parse_java_file(file_path):
    class_name = None
    dependencies = set()
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
        class_match = re.search(r"\bclass\s+(\w+)", content)
        if class_match:
            class_name = class_match.group(1)
        imports = re.findall(r"import\s+([\w.]+)\.(\w+);", content)
        for _, imported_class in imports:
            dependencies.add(imported_class)
        references = re.findall(r"\b(\w+)\s+\w+\s*[\(\)=;]", content)
        for ref in references:
            if ref != class_name:
                dependencies.add(ref)
    return class_name, dependencies

def build_dependency_graph(project_dir):
    java_files = find_java_files(project_dir)
    class_dependencies = {}
    for file in java_files:
        class_name, dependencies = parse_java_file(file)
        if class_name:
            class_dependencies[class_name] = dependencies
    return class_dependencies

def visualize_with_networkx(class_dependencies):
    G = nx.DiGraph()
    for class_name, dependencies in class_dependencies.items():
        for dep in dependencies:
            if dep in class_dependencies:
                G.add_edge(class_name, dep)
    plt.figure(figsize=(10, 6))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, node_color="lightblue", edge_color="gray", node_size=2000, font_size=10)
    plt.title("Class Dependency Graph")
    plt.show()

if __name__ == "__main__":
    project_path = "C:/Users/LaptopKhanhTran/Desktop/Workspace/JavaWorkspace/onlineAuctionPlatform"  # Change this to your project directory
    dependencies = build_dependency_graph(project_path)
    print(dependencies)
    visualize_with_networkx(dependencies)