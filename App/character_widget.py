from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QFrame, QFileDialog, QGraphicsScene, QMessageBox
from test_widget import Ui_Form
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap 
import json

class CharacterWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.test_widget = Ui_Form()

        self.test_widget.setupUi(self)
        self.scene = QGraphicsScene()
        self.test_widget.graphicsView.setScene(self.scene)
        self.scene_2 = QGraphicsScene()
        self.test_widget.graphicsView_2.setScene(self.scene_2)

        
        self.char_item = None
        self.monster_item = None
        # Load existing character data if available
        try:
            with open("characters.json", "r") as file:
                characters = json.load(file)
        except FileNotFoundError:
            characters = {}
        
        modDict = {
            'Strength':'',
            'Dexterity':'',
            'Constitution':'',
            'Intelligence':'',
            'Wisdom':'',
            'Charisma':''
        }
        turnFactors = {
            'Melee':'',
            'Ranged':'',
            'Ranged Spell':'',
            'Spell CC':''
        }
        weapons = [
            ['', 
             '',
             '',
             '',
             '',
             '']
        ]

        # Update or add new character information
        characters[''] = {
            'Image': '',
            'Level': '',
            'Class': '',
            'Size': '',
            'AC': '',
            'HP': '',
            'Speed': '',
            'AbilityModifiers': modDict,
            'TurnFactors': turnFactors,
            'Weapons': weapons
        }

        # Save updated characters to JSON file
        with open("characters.json", "w") as file:
            json.dump(characters, file, indent=4)
        
        self.loadChar()

    
    def saveChar(self):
        name = self.test_widget.Name_ent.text()
        size = self.test_widget.Size_cb.currentText()
        ac = self.test_widget.AC_cb.currentText()
        hp = self.test_widget.HP_cb.currentText()
        speed = self.test_widget.Speed_cb.currentText()
        lvl = self.test_widget.Lvl_cb.currentText()
        dnd_class = self.test_widget.class_cb.currentText()
        modDict = {
            'Strength':self.test_widget.Str_cb.currentText(),
            'Dexterity':self.test_widget.Dex_cb.currentText(),
            'Constitution':self.test_widget.Con_cb.currentText(),
            'Intelligence':self.test_widget.Int_CB.currentText(),
            'Wisdom':self.test_widget.Wis_cb.currentText(),
            'Charisma':self.test_widget.Char_cb.currentText()
        }
        turnFactors = {
            'Melee':self.test_widget.Melee_tf_cb.currentText(),
            'Ranged':self.test_widget.Ranged_tf_cb.currentText(),
            'Ranged Spell':self.test_widget.RangedSpell_tf_cb.currentText(),
            'Spell CC':self.test_widget.SpellCC_tf_cb.currentText()
        }
        weapons = [
            [self.test_widget.WeapName_ent.text(), 
             self.test_widget.WeapType_cb.currentText(),
             self.test_widget.NumDice_cb.currentText(),
             self.test_widget.DiceType_cb.currentText(),
             self.test_widget.DmgMod_cb.currentText(),
             self.test_widget.AttackMod_cb.currentText()]
        ]
        # grab curr image and save it in new path
        image_path = ''
        if self.scene is not None:
            pix = self.scene.items()[0].pixmap()
            image_path = str(name) + '_image.png'
            pix.save(image_path)
        # Load existing character data if available
        try:
            with open("characters.json", "r") as file:
                characters = json.load(file)
        except FileNotFoundError:
            characters = {}
        
        # Update or add new character information
        characters[name] = {
            'Image': image_path,
            'Level': lvl,
            'Class': dnd_class,
            'Size': size,
            'AC': ac,
            'HP': hp,
            'Speed': speed,
            'AbilityModifiers': modDict,
            'TurnFactors': turnFactors,
            'Weapons': weapons
        }
        
        # Save updated characters to JSON file
        with open("characters.json", "w") as file:
            json.dump(characters, file, indent=4)
        
        self.loadChar()
    
    def loadChar(self):
        # Load existing character data if available
        print('Loaded Called')
        try:
            with open("characters.json", "r") as file:
                characters = json.load(file)
        except FileNotFoundError:
            characters = {}
        

        print('clearing')
        self.test_widget.LoadChar_cb.clear()
        self.test_widget.LoadChar_cb.addItems(characters)
    
    def updateCharInfo(self):
        selected_character = self.test_widget.LoadChar_cb.currentText()
        print('Updating to: ', selected_character)

        try:
            with open("characters.json", "r") as file:
                characters = json.load(file)
                character_info = characters[selected_character]
        except FileNotFoundError:
            pass

        self.test_widget.Name_ent.setText(selected_character)
        self.test_widget.Size_cb.setCurrentText(character_info['Size'])
        self.test_widget.AC_cb.setCurrentText(character_info['AC'])
        self.test_widget.HP_cb.setCurrentText(character_info['HP'])
        self.test_widget.Speed_cb.setCurrentText(character_info['Speed'])
        self.test_widget.Lvl_cb.setCurrentText(character_info['Level'])
        self.test_widget.class_cb.setCurrentText(character_info['Class'])
        self.test_widget.Str_cb.setCurrentText(character_info['AbilityModifiers']['Strength'])
        self.test_widget.Dex_cb.setCurrentText(character_info['AbilityModifiers']['Dexterity'])
        self.test_widget.Con_cb.setCurrentText(character_info['AbilityModifiers']['Constitution'])
        self.test_widget.Int_CB.setCurrentText(character_info['AbilityModifiers']['Intelligence'])
        self.test_widget.Wis_cb.setCurrentText(character_info['AbilityModifiers']['Wisdom'])
        self.test_widget.Char_cb.setCurrentText(character_info['AbilityModifiers']['Charisma'])
        
        self.test_widget.Melee_tf_cb.setCurrentText(character_info['TurnFactors']['Melee'])
        self.test_widget.Ranged_tf_cb.setCurrentText(character_info['TurnFactors']['Ranged'])
        self.test_widget.RangedSpell_tf_cb.setCurrentText(character_info['TurnFactors']['Ranged Spell'])
        self.test_widget.SpellCC_tf_cb.setCurrentText(character_info['TurnFactors']['Spell CC'])
        
        self.test_widget.WeapName_ent.setText(character_info['Weapons'][0][0])
        self.test_widget.WeapType_cb.setCurrentText(character_info['Weapons'][0][1])
        self.test_widget.NumDice_cb.setCurrentText(character_info['Weapons'][0][2])
        self.test_widget.DiceType_cb.setCurrentText(character_info['Weapons'][0][3])
        self.test_widget.DmgMod_cb.setCurrentText(character_info['Weapons'][0][4])
        self.test_widget.AttackMod_cb.setCurrentText(character_info['Weapons'][0][5])
        self.scene = QGraphicsScene()
        self.test_widget.graphicsView.setScene(self.scene)
        if character_info['Image'] != '':
            
            pixmap = QPixmap(character_info['Image'])
            self.char_item = self.scene.addPixmap(pixmap)
            self.test_widget.graphicsView.fitInView(self.scene.sceneRect())

    def importChar(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, 'Import Character', '', 'Image Files (*.png *.jpg *.jpeg)')
        if file_path:
            pixmap = QPixmap(file_path)
            if self.char_item is not None:
                #self.scene.removeItem(self.char_item)
                self.scene = QGraphicsScene()
                self.test_widget.graphicsView.setScene(self.scene)
            self.char_item = self.scene.addPixmap(pixmap)
            
            self.test_widget.graphicsView.fitInView(self.scene.sceneRect())

    def delChar(self):
        selected_character = self.test_widget.LoadChar_cb.currentText()
        confirm_dialog = QMessageBox()
        confirm_dialog.setIcon(QMessageBox.Question)
        confirm_dialog.setWindowTitle("Confirm Deletion")
        confirm_dialog.setText(f"Are you sure you want to delete {selected_character}?")
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        # Execute the dialog and check the result
        result = confirm_dialog.exec_()
        
        if result == QMessageBox.Yes:
            # User confirmed deletion
            # Here, you would remove the character from characters.json
            # Implement the logic to remove the character from the file
            try:
                with open("characters.json", "r") as file:
                    characters = json.load(file)
            except FileNotFoundError:
                characters = {}

            # Update or add new character information
            del characters[selected_character]

            # Save updated characters to JSON file
            with open("characters.json", "w") as file:
                json.dump(characters, file, indent=4)
            
            self.loadChar()
        else:
            # User canceled deletion
            print('Dont Delete')

    def loadCharWeapon(self):
        print('Loading Weapon')
    
    def updateCharWeapon(self, area, grid):
        print('Updating weapon')
        numWeaps = self.test_widget.AddWeapon_cb.currentText()

        for i in range(int(numWeaps)):
            print(i)