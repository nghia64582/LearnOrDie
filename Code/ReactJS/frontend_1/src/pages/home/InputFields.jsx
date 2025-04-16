import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectItem } from "@/components/ui/select";

const vocabularyListsMock = [
  {
    id: 1,
    title: "Animals",
    topic: "Nature",
    createdAt: "2025-04-01",
    words: ["Dog", "Cat", "Elephant"],
  },
  {
    id: 2,
    title: "Technology Terms",
    topic: "Tech",
    createdAt: "2025-04-02",
    words: ["Server", "Client", "Protocol"],
  },
];

const InputFields = () => {
  const [vocabLists, setVocabLists] = useState(vocabularyListsMock);
  const [showForm, setShowForm] = useState(false);
  const [newWord, setNewWord] = useState("");
  const [topic, setTopic] = useState("Nature");

  const handleAddWord = () => {
    const updatedLists = vocabLists.map((list) => {
      if (list.topic === topic) {
        return { ...list, words: [...list.words, newWord] };
      }
      return list;
    });
    setVocabLists(updatedLists);
    setNewWord("");
    setShowForm(false);
  };

  return (
    <div className="p-4 space-y-6">
      <h1 className="text-2xl font-bold">My Vocabulary Lists</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {vocabLists.map((list) => (
          <Card key={list.id} className="shadow-md">
            <CardContent className="p-4 space-y-2">
              <h2 className="text-xl font-semibold">{list.title}</h2>
              <p className="text-sm text-gray-500">Topic: {list.topic}</p>
              <p className="text-sm text-gray-500">Created: {list.createdAt}</p>
              <p className="text-sm">Size: {list.words.length} words</p>
              <ul className="list-disc list-inside text-sm">
                {list.words.slice(0, 5).map((word, i) => (
                  <li key={i}>{word}</li>
                ))}
                {list.words.length > 5 && <li className="italic text-gray-400">...</li>}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="pt-6 flex justify-center">
        <Button onClick={() => setShowForm(true)}>Add New Word</Button>
      </div>

      {showForm && (
        <div className="p-4 border mt-4 rounded-lg shadow-sm max-w-md mx-auto space-y-4">
          <Input
            placeholder="Enter new word"
            value={newWord}
            onChange={(e) => setNewWord(e.target.value)}
          />
          <Select value={topic} onValueChange={(val) => setTopic(val)}>
            {[...new Set(vocabLists.map((l) => l.topic))].map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </Select>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button onClick={handleAddWord}>Submit</Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InputFields;
