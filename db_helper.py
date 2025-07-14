from flask import Flask, render_template, request, jsonify
import mysql.connector
import re

# DB config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Udhaya@26112004',
    'database': 'college_chatbot'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)


def handle_db_query(user_input):
    
    user_input = user_input.lower()
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        dept_aliases = {
            "cse": "Computer Science",
            "ece": "Electronics",
            "IT": "Information Tech",
            "eee": "Electrical",
            "mech": "Mechanical",
            "civil": "Civil",
            "computer science": "Computer Science",
            "electronics": "Electronics",
            "mechanical": "Mechanical",
            "electrical": "Electrical",
            "information tech": "Information Tech"
        }
        for key, dept in dept_aliases.items():
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, user_input, re.IGNORECASE) and any(word in user_input for word in ["department", "students", "from", "in"]):
                cursor.execute("SELECT * FROM students WHERE department = %s", (dept,))
                results = cursor.fetchall()
                if results:
                    response = f"Students from {dept} department:\n"
                    for i, row in enumerate(results, 1):
                        response += (
                            f"{i}. Name: {row['name']}, Roll No: {row['roll_number']}, Dept: {row['department']}, "
                            f"DOB: {row['date_of_birth']}, Gender: {row['gender']}, CGPA: {row['cgpa']}, "
                            f"City: {row['location']}, Resident: {row['resident_type']}\n"
                        )
                    return response.strip()
                else:
                    return f"No students found in {dept} department."

        # Handle unmatched departments with clear replies
        if "ai&ds" in user_input or "ai & ds" in user_input or "aids" in user_input:
            return "No students found in AI & DS department."

        if "agri" in user_input or "agriculture" in user_input:
            return "No students found in Agriculture department."

        if "bme" in user_input or "biomedical" in user_input:
            return "No students found in Bio Medical department."

        if "what is your name" in user_input or "what's your name" in user_input or "who are you" in user_input or "who r u" in user_input:
            return "My name is Buddy AI!"

        # Friend-specific
        if "who is your friend" in user_input:
            return "Udhaya is my only friend."

        if "who am i to you" in user_input:
            return "You are my friend! I'm your AI Companion too."

        # Owner-specific
        if "who is your owner" in user_input:
            return "Udhaya is my owner."

        # Creator-specific
        if "who made you" in user_input:
            return "Udhaya created me."

        if "how are you" in user_input:
            return "I'm just a bot, but I'm functioning perfectly! How can I assist you?"

        if "what can you do" in user_input or "tasks" in user_input or "help" in user_input:
            return (
                "I can assist with:\n"
                "- Any general queries\n"
                "- I can create ,update , delete a file \n"
                "- I can generate an image \n"
                "- I can read a file \n"
                "- I can answer any queries related to the students database\n"
                "- And general greetings!\n"
            )

        if "highest cgpa" in user_input or "topper" in user_input:
            cursor.execute("SELECT name, cgpa FROM students ORDER BY cgpa DESC LIMIT 1")
            result = cursor.fetchone()
            return f"{result['name']} has the highest CGPA of {result['cgpa']:.2f}."

        if "lowest cgpa" in user_input or "lowest marks" in user_input or "less cgpa" in user_input:
            cursor.execute("SELECT name, cgpa FROM students ORDER BY cgpa ASC LIMIT 1")
            result = cursor.fetchone()
            return f"{result['name']} has the lowest CGPA of {result['cgpa']:.2f}."

        if "top" in user_input and "cgpa" in user_input:
            match = re.search(r'top (\d+)', user_input)
            count = int(match.group(1)) if match else 5
            cursor.execute("SELECT name, cgpa FROM students ORDER BY cgpa DESC LIMIT %s", (count,))
            results = cursor.fetchall()
            return "Top students by CGPA:\n" + "\n".join(
                f"{i+1}. {s['name']} - CGPA: {s['cgpa']:.2f}" for i, s in enumerate(results)
            )

        if "how many" in user_input and "students" in user_input:
            cursor.execute("SELECT COUNT(*) AS total FROM students")
            count = cursor.fetchone()["total"]
            return f"There are {count} students in the database."

        if "hostel" in user_input:
            cursor.execute("SELECT COUNT(*) AS total FROM students WHERE resident_type='Hostel'")
            count = cursor.fetchone()['total']
            return f"Total hostel students: {count}"

        if "list all students" in user_input or "show all students" in user_input or "all student details" in user_input:
            cursor.execute("SELECT name, roll_number, department, date_of_birth, gender, cgpa, location, resident_type FROM students")
            results = cursor.fetchall()
            if not results:
                return "No students found in the database."
            response = "List of all students:\n"
            for i, row in enumerate(results, 1):
                response += (
                    f"{i}. Name: {row['name']}, Roll No: {row['roll_number']}, Dept: {row['department']}, DOB: {row['date_of_birth']}, "
                    f"Gender: {row['gender']}, CGPA: {row['cgpa']}, City: {row['location']}, Resident: {row['resident_type']}\n"
                )
            return response.strip()

        if "location" in user_input:
            cursor.execute("SELECT DISTINCT location FROM students")
            locations = [row['location'] for row in cursor.fetchall()]
            return "Students are from:\n" + ", ".join(locations)

        if "department" in user_input and "count" in user_input:
            cursor.execute("SELECT department, COUNT(*) AS count FROM students GROUP BY department")
            departments = cursor.fetchall()
            return "Department-wise student count:\n" + "\n".join(
                f"{d['department']}: {d['count']}" for d in departments
            )

        if "search" in user_input or "find" in user_input:
            if "roll number" in user_input:
                roll = re.findall(r'\b\d+\b', user_input)
                if roll:
                    cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll[0],))
                    result = cursor.fetchone()
                    if result:
                        return f"Student Found: {result['name']}, Roll No: {result['roll_number']}, CGPA: {result['cgpa']:.2f}"
                    else:
                        return "No student found with that roll number."
            elif "name" in user_input:
                name = user_input.split()[-1]
                cursor.execute("SELECT * FROM students WHERE name LIKE %s", (f"%{name}%",))
                result = cursor.fetchone()
                if result:
                    return f"Student Found: {result['name']}, Roll No: {result['roll_number']}, CGPA: {result['cgpa']:.2f}"
                else:
                    return "No student found with that name."

        if "add" in user_input and "student" in user_input:
            parts = user_input.split()
            if len(parts) >= 10:
                name = parts[2]
                roll = parts[3]
                dept = parts[4]
                dob = parts[5]
                gender = parts[6]
                cgpa = float(parts[7])
                location = parts[8]
                resident_type = parts[9]
                cursor.execute("""
                    INSERT INTO students (name, roll_number, department, date_of_birth, gender, cgpa, location, resident_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, roll, dept, dob, gender, cgpa, location, resident_type))
                connection.commit()
                return f"Student {name} added successfully."
            else:
                return "Please provide: name roll_number department DOB gender CGPA location resident_type"

        if "update" in user_input:
            parts = user_input.split()
            if len(parts) >= 4:
                roll = parts[1]
                field = parts[2].lower()
                value = parts[3]
                if field in ["cgpa", "department"]:
                    cursor.execute(f"UPDATE students SET {field} = %s WHERE roll_number = %s", (value, roll))
                    connection.commit()
                    return f"Updated {field} of {roll} to {value}."
                else:
                    return "Only CGPA or department can be updated."

        if "filter" in user_input or "sort" in user_input:
            if "gender" in user_input:
                cursor.execute("SELECT name, gender FROM students ORDER BY gender")
                rows = cursor.fetchall()
                return "Students sorted by gender:\n" + "\n".join(f"{r['name']} - {r['gender']}" for r in rows)
            elif "location" in user_input:
                cursor.execute("SELECT name, location FROM students ORDER BY location")
                rows = cursor.fetchall()
                return "Students sorted by location:\n" + "\n".join(f"{r['name']} - {r['location']}" for r in rows)
            else:
                return "Please specify gender or location to sort/filter."
        
        cursor.execute("SELECT DISTINCT location FROM students")
        cities_in_db = [row['location'].lower() for row in cursor.fetchall()]
        for city in cities_in_db:
            if f"from {city}" in user_input.lower() or city in user_input.lower():
                cursor.execute("SELECT * FROM students WHERE location = %s", (city.capitalize(),))
                results = cursor.fetchall()
                if results:
                    response = f"Students from {city.capitalize()}:\n"
                    for i, row in enumerate(results, 1):
                        response += (
                            f"{i}. Name: {row['name']}, Roll No: {row['roll_number']}, Dept: {row['department']}, "
                            f"DOB: {row['date_of_birth']}, Gender: {row['gender']}, CGPA: {row['cgpa']}, "
                            f"City: {row['location']}, Resident: {row['resident_type']}\n"
                        )
                    return response.strip()
                else:
                    return f"No students found from {city.capitalize()}."


        departments = ["cse", "ece", "eee", "it", "mech", "civil"]
        for dept in departments:
            if re.search(r'\b' + re.escape(dept) + r'\b', user_input):
                cursor.execute("SELECT name FROM students WHERE department = %s", (dept.upper(),))
                results = cursor.fetchall()
                if results:
                    names = ", ".join(row['name'] for row in results)
                    return f"Students in {dept.upper()} department: {names}"
                else:
                    return f"No students found in {dept.upper()} department."

        return None

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        cursor.close()
        connection.close()
