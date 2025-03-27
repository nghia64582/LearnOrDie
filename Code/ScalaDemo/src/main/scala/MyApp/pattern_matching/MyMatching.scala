package MyApp.pattern_matching

trait Comparable[A] {
  def compareInt(o1: A, o2: A): Int
}

class Student(val name: String, val score: Int) extends Comparable[Student] {

  override def compareInt(s1: Student, s2: Student): Int = {
    Integer.compare(s1.score, s2.score)
  }

}

object MyMatching {

  private abstract class Person
  private case class Student(name: String, age: Int) extends Person
  private case class Teacher(name: String, subject: String) extends Person

  def main(args : Array[String]): Unit = {
    def describe(person: Person): Unit = person match {
      case Student(name, age) => println("Student name : " + name + " age " + age)
      case Teacher(name, subject) => println("Teacher name : " + name + " subject " + subject)
    }

    val teacher1: Teacher = Teacher("Hoa", "Sinh")
    val teacher2: Teacher = Teacher("Lien", "Anh")
    val teacher3: Teacher = Teacher("Huong", "Toan")
    val student1: Student = Student("Hoa", 12)
    val student2: Student = Student("Lien", 13)
    val student3: Student = Student("Huong", 14)
    describe(teacher1)
    describe(teacher2)
    describe(teacher3)
    describe(student1)
    describe(student2)
    describe(student3)
  }

}
