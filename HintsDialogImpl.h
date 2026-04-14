#ifndef HINTSDIALOGIMPL_H
#define HINTSDIALOGIMPL_H

#include <QDialog>
#include <QKeyEvent>
#include <QDateTime>
#include <QFileDialog>
#include <QFile>
#include <QTextStream>


namespace Ui {
class HintsDialogImpl;
}

class HintsDialogImpl : public QDialog
{
    Q_OBJECT
public:
    explicit HintsDialogImpl(QWidget *parent = 0);
    ~HintsDialogImpl();

    void    setTitle( QString   sTitle );
    void    setIcon ( QIcon     Icon   );

    void    setFromFile( QString    sFile );
    void    setFromHtml( QString    sHtml, bool bScroll );

    QString toHtml( void );

public slots:
    void    exportHtml( void );

protected:

    void keyPressEvent( QKeyEvent * );

private:
    Ui::HintsDialogImpl *ui;
};

#endif // HINTSDIALOGIMPL_H
